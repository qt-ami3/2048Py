import threading
import time
import numpy as np
from pedalboard import Pedalboard, LowpassFilter
from pedalboard.io import AudioFile
import sounddevice as sd


class AudioManager:
    """Streams music with real-time pedalboard effects based on board vacancy.

    Architecture: a producer thread reads source audio, resamples, and applies
    effects into a lock-free ring buffer.  The sounddevice callback just copies
    from the ring buffer — zero allocations, no GC pressure in the audio path.
    """

    RING_CAPACITY = 1 << 17  # 131072 samples (~2.7 s at 48 kHz)

    def __init__(self, music_path, block_size=2048):
        with AudioFile(music_path) as f:
            self.audio_data = f.read(f.frames)
            self.sample_rate = f.samplerate

        self.channels = self.audio_data.shape[0]
        self.total_samples = self.audio_data.shape[1]
        self.position = 0
        self.block_size = block_size
        self.running = True

        # Effect chain (mutated only by producer thread)
        self.lowpass = LowpassFilter(cutoff_frequency_hz=20000.0)
        self.board = Pedalboard([self.lowpass])

        # Transition targets (set by game thread, read by producer)
        self.target_speed = 1.0
        self.target_cutoff = 20000.0

        # Current values (owned by producer thread only)
        self._speed = 1.0
        self._cutoff = 20000.0
        self._lerp_rate = 0.03

        # Ring buffer — producer writes, callback reads.
        # CPython int assignment is atomic under the GIL, so the single-
        # producer / single-consumer index pattern is safe without locks.
        self._ring = np.zeros((self.channels, self.RING_CAPACITY), dtype=np.float32)
        self._write = 0
        self._read = 0

        # Pre-fill ring buffer before starting the stream so the callback
        # has audio ready from the very first invocation.
        self._prefill()

        # Start producer, then output stream
        self._producer = threading.Thread(target=self._produce, daemon=True)
        self._producer.start()

        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=block_size,
            callback=self._callback,
            dtype='float32',
        )
        self.stream.start()

    # -- producer thread ------------------------------------------------

    def _prefill(self):
        """Fill ring buffer halfway before playback starts."""
        target = self.RING_CAPACITY // 2
        while self._available_to_read() < target:
            self._produce_block()

    def _produce(self):
        while self.running:
            free = self.RING_CAPACITY - 1 - self._available_to_read()
            if free < self.block_size:
                time.sleep(0.002)
                continue
            self._produce_block()

    def _produce_block(self):
        chunk_frames = self.block_size

        # Smooth parameter interpolation
        self._speed += (self.target_speed - self._speed) * self._lerp_rate
        self._cutoff += (self.target_cutoff - self._cutoff) * self._lerp_rate

        # Read source samples (fewer → slower playback)
        read_n = max(int(chunk_frames * self._speed), 1)
        src = self._read_source(read_n)

        # Resample to chunk_frames length
        if src.shape[1] != chunk_frames:
            indices = np.linspace(0, src.shape[1] - 1, chunk_frames)
            src_idx = np.arange(src.shape[1])
            out = np.empty((self.channels, chunk_frames), dtype=np.float32)
            for ch in range(self.channels):
                out[ch] = np.interp(indices, src_idx, src[ch])
            src = out

        # Apply low-pass filter
        self.lowpass.cutoff_frequency_hz = self._cutoff
        processed = self.board(src, self.sample_rate)

        # Write into ring buffer
        w = self._write
        cap = self.RING_CAPACITY
        end = w + chunk_frames
        if end <= cap:
            self._ring[:, w:end] = processed[:, :chunk_frames]
        else:
            first = cap - w
            self._ring[:, w:] = processed[:, :first]
            self._ring[:, :chunk_frames - first] = processed[:, first:chunk_frames]
        self._write = end % cap

    def _read_source(self, n):
        """Read *n* samples from the source with looping."""
        end = self.position + n
        if end <= self.total_samples:
            chunk = self.audio_data[:, self.position:end]
            self.position = end % self.total_samples
        else:
            part1 = self.audio_data[:, self.position:]
            rem = n - part1.shape[1]
            part2 = self.audio_data[:, :rem % self.total_samples]
            chunk = np.concatenate([part1, part2], axis=1)
            self.position = rem % self.total_samples
        return chunk

    # -- audio callback (real-time, no allocations) ---------------------

    def _available_to_read(self):
        return (self._write - self._read) % self.RING_CAPACITY

    def _callback(self, outdata, frames, time_info, status):
        r = self._read
        available = (self._write - r) % self.RING_CAPACITY
        if available < frames:
            outdata[:] = 0
            return
        cap = self.RING_CAPACITY
        end = r + frames
        if end <= cap:
            outdata[:] = self._ring[:, r:end].T
        else:
            first = cap - r
            outdata[:first] = self._ring[:, r:].T
            outdata[first:frames] = self._ring[:, :frames - first].T
        self._read = end % cap

    # -- public API -----------------------------------------------------

    def update(self, vacancy_ratio):
        """Call each frame. vacancy_ratio = empty_cells / total_cells."""
        if vacancy_ratio < 0.20:
            self.target_speed = 0.75
            self.target_cutoff = 800.0
        else:
            self.target_speed = 1.0
            self.target_cutoff = 20000.0

    def stop(self):
        self.running = False
        self.stream.stop()
        self.stream.close()
