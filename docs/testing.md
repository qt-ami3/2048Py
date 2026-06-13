# Test Harness

Headless pytest suite for the C++ engine. No display, audio, or game assets needed — it drives `game2048_engine` directly. Its job is catching **feature-interaction regressions**: the class of bug where two mechanics (slow tiles, contrarians, bombs, freezes, snails, walls, expansion) collide in an unplanned way.

## Running

```bash
src/venv/bin/pip install pybind11 pytest   # once
bash compile.sh                            # build the engine
src/venv/bin/python3 -m pytest tests/ -q
```

## Layout

| File | Purpose |
|------|---------|
| `tests/helpers.py` | Engine factory, grid builders, `check_invariants()`, `fuzz_run()` |
| `tests/test_determinism.py` | Same seed + same inputs ⇒ identical runs |
| `tests/test_movement_basics.py` | Plain compaction / merge / invalid-move baseline |
| `tests/test_interactions.py` | Feature-pair characterization tests + known-bug repros |
| `tests/test_fuzz_invariants.py` | Random move/ability sequences, invariants checked every turn |

## Determinism

`GameEngine(rows, cols, seed)` drives all engine RNGs from one seed. Every fuzz failure message carries `seed=N step=M` — rerunning that seed reproduces the failure exactly. Scenario tests use fixed seeds; a few note that the seed was chosen so random spawns land clear of the cells under test.

## Invariants (checked between turns)

- Grid size and tile values are valid; passives only appear on numbered tiles.
- Every active `SlowMoverState` sits on a numbered tile holding its tracked value, at a unique in-bounds position, with an in-bounds destination.
- An invalid turn (`board_changed == False`) leaves board, score, and spawn untouched.
- Score delta equals `points_gained`, which equals the sum of all three merge channels.
- Positive tile value enters only via spawns and leaves only via bombs (conservation).
- Walls never move; only bombs remove them.

## xfail conventions

- **Known-bug repros** in `test_interactions.py` are `xfail(strict=True)`: they fail today by design and turn into a loud failure (XPASS) the moment the bug is fixed — then delete the marker.
- **The fuzzer** is `xfail(strict=False)` while known bugs make most seeds fail. Once those bugs are fixed, **remove the marker** so the fuzzer becomes a hard gate. While the marker is present, new bug classes can hide inside the xfail — reclassify failures when touching engine internals.

## Adding a feature?

1. Write interaction-pair tests against each existing mechanic it can touch (use `make_engine()` + `set_grid()` to construct exact boards).
2. Run the fuzzer; investigate any new failure class before shipping.
3. When behavior is a deliberate design choice, encode it as a characterization test with a comment — that turns silent drift into a failing test.
