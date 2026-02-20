//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "game_engine.h"
#include "passive.h"
#include "slow_mover.h"
#include "random_mover.h"
#include "movement.h"
#include "passive_roller.h"

namespace py = pybind11;

PYBIND11_MODULE(game2048_engine, m) {
    m.doc() = "2048 game engine with passive ability system";

    // PassiveType enum
    py::enum_<PassiveType>(m, "PassiveType")
        .value("NONE", PassiveType::NONE)
        .value("A_LITTLE_SLOW", PassiveType::A_LITTLE_SLOW)
        .value("CONTRARIAN", PassiveType::CONTRARIAN);

    m.def("passive_name", &passive_name);
    m.def("passive_name", [](int t) { return passive_name(static_cast<PassiveType>(t)); });
    m.def("passive_description", &passive_description);
    m.def("passive_description", [](int t) { return passive_description(static_cast<PassiveType>(t)); });

    // MoveInfo
    py::class_<MoveInfo>(m, "MoveInfo")
        .def_readonly("start_row", &MoveInfo::start_row)
        .def_readonly("start_col", &MoveInfo::start_col)
        .def_readonly("end_row", &MoveInfo::end_row)
        .def_readonly("end_col", &MoveInfo::end_col)
        .def_readonly("value", &MoveInfo::value);

    // MergeInfo
    py::class_<MergeInfo>(m, "MergeInfo")
        .def_readonly("row", &MergeInfo::row)
        .def_readonly("col", &MergeInfo::col)
        .def_readonly("new_value", &MergeInfo::new_value);

    // PassiveCandidate
    py::class_<PassiveCandidate>(m, "PassiveCandidate")
        .def_readonly("row", &PassiveCandidate::row)
        .def_readonly("col", &PassiveCandidate::col)
        .def_readonly("tile_value", &PassiveCandidate::tile_value);

    // SlowMoverUpdate
    py::class_<SlowMoverUpdate>(m, "SlowMoverUpdate")
        .def_readonly("old_row", &SlowMoverUpdate::old_row)
        .def_readonly("old_col", &SlowMoverUpdate::old_col)
        .def_readonly("new_row", &SlowMoverUpdate::new_row)
        .def_readonly("new_col", &SlowMoverUpdate::new_col)
        .def_readonly("value", &SlowMoverUpdate::value)
        .def_readonly("finished", &SlowMoverUpdate::finished);

    // SlowMoverState
    py::class_<SlowMoverState>(m, "SlowMoverState")
        .def_readonly("current_row", &SlowMoverState::current_row)
        .def_readonly("current_col", &SlowMoverState::current_col)
        .def_readonly("dest_row", &SlowMoverState::dest_row)
        .def_readonly("dest_col", &SlowMoverState::dest_col)
        .def_readonly("value", &SlowMoverState::value)
        .def_readonly("active", &SlowMoverState::active);

    // RandomMoverUpdate
    py::class_<RandomMoverUpdate>(m, "RandomMoverUpdate")
        .def_readonly("old_row", &RandomMoverUpdate::old_row)
        .def_readonly("old_col", &RandomMoverUpdate::old_col)
        .def_readonly("new_row", &RandomMoverUpdate::new_row)
        .def_readonly("new_col", &RandomMoverUpdate::new_col);

    // RandomMoverState
    py::class_<RandomMoverState>(m, "RandomMoverState")
        .def_readonly("row", &RandomMoverState::row)
        .def_readonly("col", &RandomMoverState::col);

    // TurnResult
    py::class_<TurnResult>(m, "TurnResult")
        .def_readonly("moves", &TurnResult::moves)
        .def_readonly("merges", &TurnResult::merges)
        .def_readonly("bomb_destroyed", &TurnResult::bomb_destroyed)
        .def_readonly("points_gained", &TurnResult::points_gained)
        .def_readonly("spawned_tile", &TurnResult::spawned_tile)
        .def_readonly("board_changed", &TurnResult::board_changed)
        .def_readonly("should_expand", &TurnResult::should_expand)
        .def_readonly("expand_direction", &TurnResult::expand_direction)
        .def_readonly("passive_candidates", &TurnResult::passive_candidates)
        .def_readonly("slow_mover_updates", &TurnResult::slow_mover_updates)
        .def_readonly("random_mover_updates", &TurnResult::random_mover_updates)
        .def_readonly("spawned_snail", &TurnResult::spawned_snail)
        .def_readonly("snail_bomb_kills", &TurnResult::snail_bomb_kills)
        .def_readonly("slow_tile_moves", &TurnResult::slow_tile_moves)
        .def_readonly("slow_tile_merges", &TurnResult::slow_tile_merges);

    // GameEngine
    py::class_<GameEngine>(m, "GameEngine")
        .def(py::init<int, int>())
        .def("process_move", &GameEngine::process_move)
        .def("set_tile", &GameEngine::set_tile, py::arg("row"), py::arg("col"), py::arg("value"), py::arg("passive_type") = 0)
        .def("assign_passive", &GameEngine::assign_passive)
        .def("place_bomb", &GameEngine::place_bomb)
        .def("place_freeze", &GameEngine::place_freeze)
        .def("clear_freeze", &GameEngine::clear_freeze)
        .def("get_grid_values", &GameEngine::get_grid_values)
        .def("get_passive_map", &GameEngine::get_passive_map)
        .def("get_slow_movers", &GameEngine::get_slow_movers)
        .def("get_random_movers", &GameEngine::get_random_movers)
        .def("rows", &GameEngine::rows)
        .def("cols", &GameEngine::cols)
        .def("score", &GameEngine::score)
        .def("tar_expand", &GameEngine::tar_expand)
        .def("complete_expansion", &GameEngine::complete_expansion);
}
