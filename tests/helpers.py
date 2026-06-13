"""Shared helpers for the engine test harness.

Importing this module makes the compiled engine importable (it lives in src/).
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import game2048_engine as eng  # noqa: E402

# Passive bitmask flags (mirror PassiveType)
SLOW = 1
CONTRARIAN = 2
SLOW_CONTRARIAN = 3

EMPTY, BOMB, SNAIL, WALL = 0, -1, -2, -3

DIRECTIONS = ["left", "right", "up", "down"]


def make_engine(rows=4, cols=4, seed=42):
    """Seeded engine with the two random starting tiles cleared, for scenario setup."""
    e = eng.GameEngine(rows, cols, seed)
    for r in range(rows):
        for c in range(cols):
            e.set_tile(r, c, 0)
    return e


def grid(e):
    flat = e.get_grid_values()
    cols = e.cols()
    return [flat[i:i + cols] for i in range(0, len(flat), cols)]


def set_grid(e, rows_vals, passives=None):
    """rows_vals: list of row lists. passives: {(r, c): bitmask}."""
    passives = passives or {}
    for r, row in enumerate(rows_vals):
        for c, v in enumerate(row):
            e.set_tile(r, c, v, passives.get((r, c), 0))


def cell(e, r, c):
    return grid(e)[r][c]


def passive_map(e):
    return {(r, c): p for r, c, p in e.get_passive_map()}


def grid_minus_spawn(e, result):
    """Board with the tile spawned by this turn zeroed out, so scenario tests can
    assert expected grids without caring where the random spawn landed.
    (The spawn always lands on a cell that is empty post-move, so zeroing is safe.)
    """
    g = grid(e)
    sr, sc = result.spawned_tile
    if sr >= 0:
        g[sr][sc] = 0
    return g


def active_slow_movers(e):
    return [sm for sm in e.get_slow_movers() if sm.active]


def is_power_of_two(v):
    return v >= 2 and (v & (v - 1)) == 0


def check_invariants(e, context=""):
    """Structural invariants that must hold between any two turns."""
    rows, cols = e.rows(), e.cols()
    flat = e.get_grid_values()
    assert len(flat) == rows * cols, f"{context}: grid size {len(flat)} != {rows}x{cols}"
    g = grid(e)

    for r in range(rows):
        for c in range(cols):
            v = g[r][c]
            assert v in (EMPTY, BOMB, SNAIL, WALL) or is_power_of_two(v), \
                f"{context}: invalid tile value {v} at {(r, c)}"

    for (r, c), p in passive_map(e).items():
        assert 1 <= p <= 3, f"{context}: invalid passive bitmask {p} at {(r, c)}"
        assert g[r][c] >= 2, \
            f"{context}: passive {p} on non-numbered tile (value {g[r][c]}) at {(r, c)}"

    seen = set()
    for sm in active_slow_movers(e):
        r, c = sm.current_row, sm.current_col
        assert 0 <= r < rows and 0 <= c < cols, \
            f"{context}: slow mover out of bounds at {(r, c)}"
        assert 0 <= sm.dest_row < rows and 0 <= sm.dest_col < cols, \
            f"{context}: slow mover destination out of bounds {(sm.dest_row, sm.dest_col)}"
        assert (r, c) not in seen, f"{context}: two active slow movers at {(r, c)}"
        seen.add((r, c))
        assert g[r][c] == sm.value, \
            f"{context}: slow mover at {(r, c)} tracks value {sm.value}, board holds {g[r][c]}"


def fuzz_run(seed, steps=250, check=True):
    """Random move/ability sequence mirroring real frontend usage.

    Returns a log of (grid, score) per step so determinism tests can compare runs.
    With check=True, asserts structural and accounting invariants every step.
    """
    import random
    e = eng.GameEngine(4, 4, seed)
    rng = random.Random(seed)
    log = []
    if check:
        check_invariants(e, f"seed={seed} start")

    for step in range(steps):
        ctx = f"seed={seed} step={step}"
        g = grid(e)
        rows, cols = e.rows(), e.cols()
        numbered = [(r, c) for r in range(rows) for c in range(cols) if g[r][c] >= 2]
        empties = [(r, c) for r in range(rows) for c in range(cols) if g[r][c] == 0]
        sm_cells = {(sm.current_row, sm.current_col) for sm in active_slow_movers(e)}

        # Occasionally use an ability, like a player would.
        roll = rng.random()
        if roll < 0.06 and empties:
            e.place_bomb(*rng.choice(empties))
        elif roll < 0.12 and numbered:
            e.place_freeze(*rng.choice(numbered))
        elif roll < 0.18 and len(numbered) >= 2:
            a, b = rng.sample(numbered, 2)
            e.switch_tiles(a[0], a[1], b[0], b[1])
        elif roll < 0.24:
            # Mirror the passive menu: it never targets active slow movers
            # (PassiveRoller excludes their positions from candidates).
            eligible = [p for p in numbered if p not in sm_cells]
            if eligible:
                r, c = rng.choice(eligible)
                e.assign_passive(r, c, rng.choice([SLOW, CONTRARIAN, SLOW_CONTRARIAN]))
        if check:
            check_invariants(e, ctx + " pre-move")

        before_flat = e.get_grid_values()
        before_score = e.score()
        walls_before = {(r, c) for r in range(rows) for c in range(cols)
                        if grid(e)[r][c] == WALL}

        d = rng.choice(DIRECTIONS)
        res = e.process_move(d)
        ctx = f"seed={seed} step={step} dir={d}"

        if not res.board_changed:
            if check:
                assert e.get_grid_values() == before_flat, f"{ctx}: invalid move mutated board"
                assert e.score() == before_score, f"{ctx}: invalid move changed score"
                assert res.spawned_tile == (-1, -1), f"{ctx}: invalid move spawned a tile"
            log.append((tuple(e.get_grid_values()), e.score()))
            if not e.has_moves():
                break
            continue

        if check:
            # Scoring rule: every merge of numbered tiles scores, whichever
            # phase performed it (regular, behavior advance, slow-mover arrival).
            assert e.score() == before_score + res.points_gained, ctx
            expected_points = (sum(m.new_value for m in res.merges)
                               + sum(m.new_value for m in res.slow_tile_merges)
                               + sum(u.value for u in res.slow_mover_updates if u.is_merge))
            assert res.points_gained == expected_points, ctx

            # Conservation: positive value enters only via the spawn, leaves only via bombs.
            spawn_value = 0
            sr, sc = res.spawned_tile
            if sr >= 0:
                spawn_value = grid(e)[sr][sc]
                assert spawn_value > 0, f"{ctx}: spawned tile cell holds {spawn_value}"
            before_sum = sum(v for v in before_flat if v > 0)
            after_sum = sum(v for v in e.get_grid_values() if v > 0)
            destroyed = set(res.bomb_destroyed)
            if not destroyed:
                assert after_sum == before_sum + spawn_value, \
                    f"{ctx}: value not conserved ({before_sum} + {spawn_value} -> {after_sum})"
            else:
                assert after_sum <= before_sum + spawn_value, \
                    f"{ctx}: value created from nothing ({before_sum} + {spawn_value} -> {after_sum})"

            # Walls never move; they only vanish to bombs. (Expansion adds walls,
            # but that happens in complete_expansion below, after this check.)
            walls_after = {(r, c) for r in range(e.rows()) for c in range(e.cols())
                           if grid(e)[r][c] == WALL}
            assert walls_after <= walls_before, f"{ctx}: wall appeared during a move"
            assert walls_before - walls_after <= destroyed, \
                f"{ctx}: wall vanished without a bomb"

            check_invariants(e, ctx)

        # Mirror the frontend: complete a pending expansion, resolve passive menus.
        if res.should_expand:
            e.complete_expansion(rng.choice(DIRECTIONS))
            if check:
                check_invariants(e, ctx + " post-expand")
        for cand in res.passive_candidates:
            if grid(e)[cand.row][cand.col] >= 2:
                e.assign_passive(cand.row, cand.col,
                                 rng.choice([SLOW, CONTRARIAN, SLOW_CONTRARIAN]))

        log.append((tuple(e.get_grid_values()), e.score()))
        if not e.has_moves():
            break

    return log
