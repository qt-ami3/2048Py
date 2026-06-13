"""Baseline regular-movement behavior (no passives, no abilities)."""
import helpers as H

Z = [0, 0, 0, 0]


def test_simple_merge_left():
    e = H.make_engine()
    H.set_grid(e, [[2, 2, 0, 0], Z, Z, Z])
    res = e.process_move("left")
    assert res.board_changed
    assert H.grid_minus_spawn(e, res)[0] == [4, 0, 0, 0]
    assert [(m.row, m.col, m.new_value) for m in res.merges] == [(0, 0, 4)]
    assert res.points_gained == 4
    H.check_invariants(e)


def test_double_merge_in_one_row():
    e = H.make_engine()
    H.set_grid(e, [[2, 2, 2, 2], Z, Z, Z])
    res = e.process_move("left")
    assert H.grid_minus_spawn(e, res)[0] == [4, 4, 0, 0]
    assert res.points_gained == 8
    H.check_invariants(e)


def test_odd_triple_merges_toward_movement_wall():
    e = H.make_engine()
    H.set_grid(e, [[2, 2, 2, 0], Z, Z, Z])
    res = e.process_move("left")
    # The pair closest to the wall merges; the third tile slides up behind it.
    assert H.grid_minus_spawn(e, res)[0] == [4, 2, 0, 0]
    H.check_invariants(e)


def test_invalid_move_is_a_noop():
    e = H.make_engine()
    H.set_grid(e, [[2, 0, 0, 0], Z, Z, Z])
    before = e.get_grid_values()
    score_before = e.score()
    res = e.process_move("left")  # tile already at the wall, nothing can move
    assert not res.board_changed
    assert e.get_grid_values() == before
    assert e.score() == score_before
    assert res.spawned_tile == (-1, -1)


def test_valid_move_spawns_exactly_one_tile():
    e = H.make_engine()
    H.set_grid(e, [[0, 0, 0, 2], Z, Z, Z])
    occupied_before = sum(1 for v in e.get_grid_values() if v != 0)
    res = e.process_move("left")
    assert res.spawned_tile != (-1, -1)
    occupied_after = sum(1 for v in e.get_grid_values() if v != 0)
    assert occupied_after == occupied_before + 1
    H.check_invariants(e)
