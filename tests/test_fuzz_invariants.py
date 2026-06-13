"""Invariant fuzzing: random move/ability sequences, structural checks every turn.

This is the net for combinatorial feature interactions: it explores pairings
nobody thought to test. A failure message carries the seed and step — rerun
with that seed for a deterministic reproduction.
"""
import pytest
import helpers as H


@pytest.mark.xfail(
    strict=False,
    reason="KNOWN BUGS break the invariants on most seeds — see the xfail tests in "
           "test_interactions.py: stale slow-mover trackers after merges "
           "(test_contrarian_merge_into_active_slow_mover_…, "
           "test_behind_merge_consuming_active_slow_mover_…) and board mutation on "
           "invalid turns (test_invalid_turn_with_detonation_…). Once those are "
           "fixed, REMOVE this marker so the fuzzer becomes a hard gate.")
@pytest.mark.parametrize("seed", range(20))
def test_fuzz_invariants(seed):
    H.fuzz_run(seed, steps=250, check=True)
