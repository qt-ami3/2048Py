# Audio System

The audio system streams background music with real-time effects that react to board pressure. It lives entirely in `src/audio_manager.py` and is driven from `src/main.py`.

**Dependencies:** `pedalboard`, `sounddevice`, `numpy`

---

## Overview

| Component | Description |
|-----------|-------------|
| `AudioManager` | Loads the music track, manages a producer thread + ring buffer, and exposes an `update()` method for the game loop |
| `pedalboard` | Applies a `LowpassFilter` to audio chunks in the producer thread |
| `sounddevice` | Streams processed audio to the system audio device |

`pygame.mixer` is explicitly quit at startup (`pygame.mixer.quit()`) to free the audio device for `sounddevice`.

---

## Architecture

```
┌──────────────┐         ┌──────────────────┐         ┌────────────────┐
│  Game loop   │ update() │  Producer thread  │  ring   │  SD callback   │
│  (main.py)   │────────►│  resample + FX    │────────►│  memcpy only   │──► speakers
│  vacancy %   │         │  (audio_manager)  │ buffer  │  (real-time)   │
└──────────────┘         └──────────────────┘         └────────────────┘
```

### Why a ring buffer?

The `sounddevice` callback runs on a real-time audio thread. Any Python allocation, GC pause, or lock contention inside the callback causes buffer underruns (audible skipping). By moving all processing to a separate producer thread and having the callback just copy from a pre-filled ring buffer, the audio path is allocation-free.

| Property | Value |
|----------|-------|
| Ring capacity | 131072 samples (~2.7 s at 48 kHz) |
| Block size | 2048 samples per produce/consume cycle |
| Synchronization | Lock-free single-producer / single-consumer (CPython GIL guarantees atomic int assignment) |
| Pre-fill | Ring is filled to 50% before the stream starts |

---

## Effects

The system applies two effects when the board is under pressure:

| Condition | Speed | Low-pass cutoff |
|-----------|-------|-----------------|
| ≥ 20% vacant cells | 1.0× (normal) | 20,000 Hz (transparent) |
| < 20% vacant cells | 0.75× (slowed) | 800 Hz (muffled) |

Both parameters **smoothly interpolate** toward their targets each producer block (`lerp_rate = 0.03`), so transitions fade in/out gradually rather than snapping.

### How slowing works

The producer reads fewer source samples than the output block size, then resamples (stretches) via `numpy.interp` to fill the block. This simultaneously lowers pitch and slows tempo — the classic "slowed" effect.

### How the low-pass works

A `pedalboard.LowpassFilter` is applied to every chunk in the producer thread. Its `cutoff_frequency_hz` is updated each block to track the interpolated target.

---

## Integration with main.py

### Initialization

```python
from audio_manager import AudioManager

pygame.init()
pygame.mixer.quit()  # free audio device for sounddevice

# ... after engine setup ...
g.audio = AudioManager("assets/audio/music/2048squaredMain.mp3")
```

### Per-frame update

```python
total_cells = g.rows * g.cols
empty_cells = int(np.count_nonzero(g.playingGrid == 0))
g.audio.update(empty_cells / total_cells)
```

### Shutdown

```python
g.audio.stop()
pygame.quit()
```

---

## Game State

| Attribute | Type | Description |
|-----------|------|-------------|
| `g.audio` | `AudioManager` | Audio manager instance |

---

## File Layout

```
src/
├── assets/audio/music/
│   └── 2048squaredMain.mp3    # Background music track
├── audio_manager.py           # AudioManager class
└── main.py                    # Integration point
```

---

## Tuning

Constants in `AudioManager.__init__`:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `block_size` | 2048 | Samples per produce/consume cycle. Lower = less latency, higher CPU. |
| `RING_CAPACITY` | 131072 | Ring buffer size. Must be a power of 2. Larger = more underrun headroom. |
| `_lerp_rate` | 0.03 | Transition smoothness. Lower = slower fade, higher = snappier. |
| `target_speed` | 0.75 | Playback rate when stressed. Lower = slower + deeper pitch. |
| `target_cutoff` | 800.0 | Low-pass cutoff (Hz) when stressed. Lower = more muffled. |

The vacancy threshold (20%) is set in `AudioManager.update()`.
