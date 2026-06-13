"""Same seed + same inputs must produce identical runs.

This is the keystone of the harness: every bug the fuzzer finds is reproducible
by its seed, and scenario tests stay stable.
"""
import helpers as H


def test_same_seed_same_starting_board():
    a = H.eng.GameEngine(4, 4, 7)
    b = H.eng.GameEngine(4, 4, 7)
    assert a.get_grid_values() == b.get_grid_values()


def test_same_seed_same_full_run():
    # Full action set: moves, abilities, expansions, passive assignment.
    assert H.fuzz_run(123, steps=80, check=False) == H.fuzz_run(123, steps=80, check=False)


def test_different_seeds_diverge():
    assert H.fuzz_run(1, steps=30, check=False) != H.fuzz_run(2, steps=30, check=False)
