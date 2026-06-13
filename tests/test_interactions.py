"""Feature-pair interaction tests.

Most are characterization tests: they pin down today's behavior so that future
features changing an interaction fail loudly instead of silently. Scenarios
drawn from past bug-fix commits are noted.

Tests marked xfail(strict=True) document KNOWN bugs found by code inspection:
they fail today, and will flip to a loud failure (XPASS) once the bug is fixed,
prompting removal of the marker.
"""
import pytest
import helpers as H

Z = [0, 0, 0, 0]


# ─── Freeze ───

def test_user_frozen_tile_splits_segment():
    e = H.make_engine()
    H.set_grid(e, [[0, 4, 2, 2], Z, Z, Z])
    e.place_freeze(0, 1)
    res = e.process_move("left")
    # Frozen 4 holds; the [2, 2] segment right of it merges within its segment.
    assert H.grid_minus_spawn(e, res)[0] == [0, 4, 4, 0]
    H.check_invariants(e)


def test_freeze_expires_after_one_valid_turn():
    # Seed chosen so the turn-1 spawn lands clear of row 0; re-verify if changed.
    e = H.make_engine(seed=3)
    H.set_grid(e, [[0, 4, 0, 0], Z, Z, [0, 0, 0, 2]])
    e.place_freeze(0, 1)
    res1 = e.process_move("left")
    assert H.cell(e, 0, 1) == 4  # held in place
    res2 = e.process_move("left")
    # Freeze cleared by the previous valid turn: the 4 now slides to the wall.
    assert any((m.start_row, m.start_col) == (0, 1) for m in res2.moves)
    H.check_invariants(e)


def test_frozen_slow_tile_does_not_advance():
    # Regression scenario for commit 338fdec ("forgot to make freeze work for
    # a little slow").
    e = H.make_engine()
    H.set_grid(e, [[0, 0, 4, 0], Z, Z, [2, 0, 0, 2]], passives={(0, 2): H.SLOW})
    e.place_freeze(0, 2)
    e.process_move("left")
    assert H.cell(e, 0, 2) == 4
    assert H.passive_map(e).get((0, 2)) == H.SLOW
    assert H.active_slow_movers(e) == []
    H.check_invariants(e)


# ─── Bombs ───

def test_bomb_slide_destroys_bomb_and_victim():
    # NOTE: docs/game-systems.md says "the bomb itself survives the collision";
    # the code destroys both bomb and victim at the landing cell. Characterizing
    # the code. If the docs are right, this test (not the docs) should change.
    e = H.make_engine()
    H.set_grid(e, [[0, 0, 0, 2], Z, Z, Z])
    e.place_bomb(0, 2)
    res = e.process_move("left")
    assert H.grid_minus_spawn(e, res)[0] == [0, 0, 0, 0]
    assert (0, 0) in set(res.bomb_destroyed)
    H.check_invariants(e)


def test_bomb_between_frozen_and_normal_tile_destroys_the_normal_tile():
    # Regression scenario for commit d390c6d.
    e = H.make_engine()
    H.set_grid(e, [[4, 0, 2, 0], Z, Z, Z])
    e.place_freeze(0, 0)
    e.place_bomb(0, 1)
    res = e.process_move("left")
    # The 2 slides into the bomb; both are destroyed. The frozen 4 survives
    # (user-frozen tiles are not detonated by the pre-movement pass).
    assert H.grid_minus_spawn(e, res)[0] == [4, 0, 0, 0]
    assert (0, 1) in set(res.bomb_destroyed)
    H.check_invariants(e)


def test_bomb_sliding_against_user_frozen_tile_detonates_post_move():
    e = H.make_engine()
    H.set_grid(e, [[4, 0, 0, 0], Z, Z, Z])
    e.place_freeze(0, 0)
    e.place_bomb(0, 3)
    res = e.process_move("left")
    # Bomb slides to (0,1); the post-movement pass detonates it against the
    # frozen tile, destroying both.
    assert H.grid_minus_spawn(e, res)[0] == [0, 0, 0, 0]
    assert {(0, 0), (0, 1)} <= set(res.bomb_destroyed)
    H.check_invariants(e)


def test_bomb_adjacent_to_passive_tile_detonates_before_movement():
    # Behavior-owned tiles (slow/contrarian) are always detonatable: a bomb
    # next to one explodes in the pre-movement pass, killing both.
    e = H.make_engine()
    H.set_grid(e, [[4, 0, 0, 0], Z, Z, [0, 0, 0, 8]], passives={(0, 0): H.SLOW})
    e.place_bomb(0, 1)
    res = e.process_move("left")
    g = H.grid_minus_spawn(e, res)
    assert g[0] == [0, 0, 0, 0]
    assert {(0, 0), (0, 1)} <= set(res.bomb_destroyed)
    assert (0, 0) not in H.passive_map(e)
    H.check_invariants(e)


# ─── Walls and snails ───

def test_wall_blocks_and_splits_segment():
    e = H.make_engine()
    H.set_grid(e, [[2, H.WALL, 2, 2], Z, Z, Z])
    res = e.process_move("left")
    g = H.grid_minus_spawn(e, res)
    assert g[0] == [2, H.WALL, 4, 0]
    assert res.points_gained == 4
    H.check_invariants(e)


def test_snail_blocks_compaction_then_tile_follows_into_vacated_cell():
    e = H.make_engine()
    H.set_grid(e, [[0, H.SNAIL, 0, 2], Z, Z, Z])
    res = e.process_move("left")
    # The 2 compacts up to the snail; the snail then wanders to an adjacent
    # empty cell, and the 2 cascades into the cell it vacated (undocumented
    # rule: snail_vacated cascade in game_engine.cpp process_move).
    assert H.cell(e, 0, 1) == 2
    snails = [(r, c) for r in range(4) for c in range(4) if H.cell(e, r, c) == H.SNAIL]
    assert snails in ([(0, 0)], [(1, 1)])
    assert len(res.random_mover_updates) == 1
    H.check_invariants(e)


def test_snail_killed_by_adjacent_bomb():
    e = H.make_engine()
    H.set_grid(e, [[H.SNAIL, 0, 0, 0], Z, Z, [0, 0, 0, 8]])
    e.place_bomb(0, 1)
    res = e.process_move("left")
    assert (0, 0) in set(res.snail_bomb_kills)
    assert {(0, 0), (0, 1)} <= set(res.bomb_destroyed)
    assert all(v != H.SNAIL for v in e.get_grid_values())
    H.check_invariants(e)


# ─── Slow tiles ───

def test_slow_tile_steps_one_cell_and_tracks_destination():
    e = H.make_engine()
    H.set_grid(e, [[0, 0, 0, 2], Z, Z, [0, 0, 0, 8]], passives={(0, 3): H.SLOW})
    res = e.process_move("left")
    assert H.cell(e, 0, 2) == 2
    assert H.passive_map(e).get((0, 2)) == H.SLOW
    sms = H.active_slow_movers(e)
    assert len(sms) == 1
    assert (sms[0].current_row, sms[0].current_col) == (0, 2)
    assert (sms[0].dest_row, sms[0].dest_col) == (0, 0)
    assert any((m.start_row, m.start_col, m.end_row, m.end_col) == (0, 3, 0, 2)
               for m in res.slow_tile_moves)
    H.check_invariants(e)


def test_slow_mover_advances_one_cell_per_turn_to_destination():
    # Seed chosen so spawns land clear of the slow mover's row-0 path across
    # all three turns; re-verify if changed.
    e = H.make_engine(seed=5)
    H.set_grid(e, [[0, 0, 0, 2], Z, Z, [0, 0, 0, 8]], passives={(0, 3): H.SLOW})
    e.process_move("left")
    assert H.cell(e, 0, 2) == 2

    e.process_move("left")
    assert H.cell(e, 0, 1) == 2
    sms = H.active_slow_movers(e)
    assert len(sms) == 1 and (sms[0].current_row, sms[0].current_col) == (0, 1)

    e.process_move("left")
    assert H.cell(e, 0, 0) == 2
    assert H.active_slow_movers(e) == []  # journey finished, tracking dropped
    H.check_invariants(e)


def test_tile_compacting_behind_slow_tile_merges_into_it():
    e = H.make_engine()
    H.set_grid(e, [[0, 2, 0, 2], Z, Z, Z], passives={(0, 1): H.SLOW})
    res = e.process_move("left")
    # The regular 2 compacts to (0,2), behind-merges into the slow tile (-> 4),
    # which then advances its single step to the wall.
    g = H.grid_minus_spawn(e, res)
    assert g[0] == [4, 0, 0, 0]
    assert H.passive_map(e).get((0, 0)) == H.SLOW
    assert any((m.row, m.col, m.new_value) == (0, 1, 4) for m in res.slow_tile_merges)
    # Every merge scores, including behavior-phase merges.
    assert res.points_gained == 4
    H.check_invariants(e)


def test_slow_tile_reserves_its_behind_neighbor_for_the_merge():
    # freeze_tile_behind: the same-value tile directly behind a slow tile is
    # frozen with it, so it behind-merges instead of merging with the tile
    # behind IT during regular compaction.
    e = H.make_engine()
    H.set_grid(e, [[0, 2, 2, 2], Z, Z, Z], passives={(0, 1): H.SLOW})
    res = e.process_move("left")
    g = H.grid_minus_spawn(e, res)
    assert g[0] == [4, 0, 0, 2]
    assert H.passive_map(e).get((0, 0)) == H.SLOW
    H.check_invariants(e)


# ─── Contrarian tiles ───

def test_pure_contrarian_slides_fully_opposite():
    e = H.make_engine()
    H.set_grid(e, [[0, 2, 0, 0], Z, Z, [0, 0, 0, 8]], passives={(0, 1): H.CONTRARIAN})
    e.process_move("left")
    assert H.cell(e, 0, 3) == 2
    assert H.passive_map(e).get((0, 3)) == H.CONTRARIAN
    H.check_invariants(e)


def test_contrarian_blocked_before_movement_stays_blocked():
    # pre_blocked: a tile occupying the contrarian's path before regular
    # movement blocks it for the whole turn, even though regular movement
    # cannot actually fill that cell (it is behind the frozen contrarian).
    e = H.make_engine()
    H.set_grid(e, [[0, 2, 4, 0], Z, Z, [0, 0, 0, 8]], passives={(0, 1): H.CONTRARIAN})
    e.process_move("left")
    assert H.cell(e, 0, 1) == 2
    assert H.cell(e, 0, 2) == 4
    H.check_invariants(e)


def test_contrarian_merges_with_tile_compacted_into_its_path():
    e = H.make_engine()
    H.set_grid(e, [[2, 0, 0, 2], Z, Z, Z], passives={(0, 0): H.CONTRARIAN})
    res = e.process_move("left")
    # The regular 2 compacts to (0,1) (the contrarian splits the segment);
    # the contrarian then slides right and merges into it.
    assert H.cell(e, 0, 1) == 4
    assert H.passive_map(e).get((0, 1)) == H.CONTRARIAN
    assert any((m.row, m.col, m.new_value) == (0, 1, 4) for m in res.slow_tile_merges)
    H.check_invariants(e)


def test_slow_contrarian_steps_one_cell_opposite():
    e = H.make_engine()
    H.set_grid(e, [[0, 2, 0, 0], Z, Z, [0, 0, 0, 8]],
               passives={(0, 1): H.SLOW_CONTRARIAN})
    e.process_move("left")
    assert H.cell(e, 0, 2) == 2
    assert H.passive_map(e).get((0, 2)) == H.SLOW_CONTRARIAN
    sms = H.active_slow_movers(e)
    assert len(sms) == 1
    assert (sms[0].current_row, sms[0].current_col) == (0, 2)
    assert (sms[0].dest_row, sms[0].dest_col) == (0, 3)
    H.check_invariants(e)


# ─── Passive combination on merge (rule: merged tile carries the OR of both) ───

def test_behind_merge_combines_passives_and_tile_waits_a_turn():
    # A contrarian tile sits directly behind a slow tile; the behind-merge
    # absorbs it. The merged tile is Slow Contrarian (3) and, having changed
    # owner mid-phase, stays put until next turn.
    e = H.make_engine()
    H.set_grid(e, [[0, 2, 2, 0], Z, Z, [0, 0, 0, 8]],
               passives={(0, 1): H.SLOW, (0, 2): H.CONTRARIAN})
    res = e.process_move("left")
    assert H.cell(e, 0, 1) == 4
    assert H.passive_map(e).get((0, 1)) == H.SLOW_CONTRARIAN
    assert any((m.row, m.col, m.new_value) == (0, 1, 4) for m in res.slow_tile_merges)
    assert res.points_gained == 4
    H.check_invariants(e)


def test_slow_forward_merge_into_contrarian_combines_passives():
    # SlowBehavior runs before ContrarianBehavior, so the slow tile merges into
    # the contrarian first; the combined tile then takes the contrarian's turn
    # (one slow-contrarian step opposite the move).
    e = H.make_engine()
    H.set_grid(e, [[2, 2, 0, 0], Z, Z, [0, 0, 0, 8]],
               passives={(0, 0): H.CONTRARIAN, (0, 1): H.SLOW})
    res = e.process_move("left")
    assert H.cell(e, 0, 1) == 4
    assert H.passive_map(e).get((0, 1)) == H.SLOW_CONTRARIAN
    assert res.points_gained == 4
    H.check_invariants(e)


def test_slow_mover_arrival_merge_combines_passives():
    # A travelling slow mover arrives at a matching contrarian tile: the merge
    # combines both passives. (Seed-robust: asserts avoid the mover the
    # contrarian phase may spawn afterwards.)
    e = H.make_engine(4, 5)
    H.set_grid(e, [
        [0, 0, 0, 0, 2],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 8],
    ], passives={(0, 4): H.SLOW})
    e.process_move("left")
    sms = H.active_slow_movers(e)
    assert len(sms) == 1 and (sms[0].current_row, sms[0].current_col) == (0, 3)

    e.set_tile(0, 2, 2, H.CONTRARIAN)  # lands in the mover's path
    res = e.process_move("left")
    # Phase 6 merges the mover into it; the combined tile then takes its
    # contrarian turn, stepping one cell back to (0, 3).
    assert H.cell(e, 0, 3) == 4
    assert H.passive_map(e).get((0, 3)) == H.SLOW_CONTRARIAN
    assert any(u.is_merge and u.value == 4 for u in res.slow_mover_updates)
    assert res.points_gained == 4
    H.check_invariants(e)


# ─── Switch ───

def test_switch_drops_slow_mover_tracking():
    e = H.make_engine()
    H.set_grid(e, [[0, 0, 0, 2], Z, Z, [0, 0, 0, 8]], passives={(0, 3): H.SLOW})
    e.process_move("left")
    assert len(H.active_slow_movers(e)) == 1
    e.switch_tiles(0, 2, 2, 2)
    # Tracking is dropped; the tile (and its passive) travelled with the swap.
    assert H.active_slow_movers(e) == []
    assert H.cell(e, 2, 2) == 2
    assert H.passive_map(e).get((2, 2)) == H.SLOW
    H.check_invariants(e)


# ─── Known bugs (xfail: these document defects found by inspection) ───

@pytest.mark.xfail(
    strict=True,
    reason="BUG: contrarian merging into an active slow mover's tile leaves the "
           "SlowMoverState tracking a stale value; on a later turn it overwrites "
           "the merged tile with the old value (game_engine.cpp advance_slow_movers "
           "vs contrarian_behavior.cpp merge scan)")
def test_contrarian_merge_into_active_slow_mover_keeps_tracking_consistent():
    # Seed chosen so the turn-1 spawn lands clear of (0,1); re-verify if changed.
    e = H.make_engine(seed=2)
    H.set_grid(e, [
        [0, 0, 0, 2],          # slow tile: will step left, leaving a mover
        [0, 2, H.WALL, 0],     # contrarian, wall keeps it put on turn 1
        Z,
        [0, 0, 0, 8],          # filler so turn 1 is valid
    ], passives={(0, 3): H.SLOW, (1, 1): H.CONTRARIAN})

    e.process_move("left")
    sms = H.active_slow_movers(e)
    assert len(sms) == 1 and (sms[0].current_row, sms[0].current_col) == (0, 2)

    # Turn 2: the slow mover steps to (0,1); the contrarian (moving up, opposite
    # of "down") then merges into it. The tracker must not survive pointing at
    # the merged tile with the old value.
    e.process_move("down")
    assert H.cell(e, 0, 1) == 4
    H.check_invariants(e)  # fails today: tracker still holds value 2 at (0,1)


@pytest.mark.xfail(
    strict=True,
    reason="BUG: a slow tile's behind-merge can consume the tile of an ACTIVE slow "
           "mover that stepped in behind it, leaving the tracker pointing at an "
           "empty cell; on later turns it re-materializes the stale value "
           "(slow_behavior.cpp behind-merge has no active_sm_positions check on "
           "the behind cell)")
def test_behind_merge_consuming_active_slow_mover_keeps_tracking_consistent():
    # Seed chosen so spawns land clear of the row-0 path; re-verify if changed.
    e = H.make_engine(4, 5, seed=0)
    H.set_grid(e, [
        [0, 0, 0, 0, 2],     # slow tile: will leave a mover travelling left
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 8],     # filler so turn 1 is valid
    ], passives={(0, 4): H.SLOW})
    e.process_move("left")
    sms = H.active_slow_movers(e)
    assert len(sms) == 1 and (sms[0].current_row, sms[0].current_col) == (0, 3)

    # A matching slow tile lands in the mover's path (e.g. via the passive menu).
    e.set_tile(0, 1, 2, H.SLOW)
    # Turn 2: the mover steps to (0,2); the slow tile at (0,1) behind-merges it
    # away. The tracker must not survive pointing at the now-empty cell.
    e.process_move("left")
    H.check_invariants(e)  # fails today: tracker at (0,2) over an empty cell


@pytest.mark.xfail(
    strict=True,
    reason="BUG: pre-movement bomb detonations mutate the board even when the turn "
           "is then reported invalid (board_changed=False). The frontend skips "
           "syncing on invalid turns, so the engine and the rendered board desync "
           "(game_engine.cpp validity check ignores detonation mutations)")
def test_invalid_turn_with_detonation_must_not_mutate_board():
    e = H.make_engine()
    H.set_grid(e, [[2, 0, 0, 0], Z, Z, Z], passives={(0, 0): H.SLOW})
    e.place_bomb(0, 1)
    before = e.get_grid_values()
    res = e.process_move("left")  # nothing can move; only the detonation fires
    # Contract: an invalid turn must leave the board untouched.
    assert res.board_changed or e.get_grid_values() == before


def test_frozen_slow_mover_merge_is_reported_and_scored():
    e = H.make_engine()
    H.set_grid(e, [[0, 0, 0, 2], Z, Z, [0, 0, 0, 8]], passives={(0, 3): H.SLOW})
    e.process_move("left")  # slow tile steps to (0,2), mover tracks dest (0,0)

    e.place_freeze(0, 2)
    e.set_tile(0, 3, 2)  # matching tile sitting behind the frozen slow mover
    score_before = e.score()
    res = e.process_move("left")

    # The merge happens on the board…
    assert H.cell(e, 0, 2) == 4
    # …and must be reported and scored. Both fail today.
    assert any((m.row, m.col, m.new_value) == (0, 2, 4) for m in res.merges)
    assert e.score() == score_before + res.points_gained
    assert res.points_gained >= 4
