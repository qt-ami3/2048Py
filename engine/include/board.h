#pragma once

#include "tile.h"
#include <vector>
#include <set>
#include <tuple>
#include <utility>
#include <random>

class Board {
public:
    Board(int rows, int cols);

    int rows() const { return rows_; }
    int cols() const { return cols_; }

    Tile& at(int r, int c);
    const Tile& at(int r, int c) const;

    void expand(const std::string& direction);

    // Spawn a 2 in a random empty cell, excluding given positions. Returns (-1,-1) if no space.
    std::pair<int,int> spawn_number(const std::set<std::pair<int,int>>& excluded = {});

    // Place a bomb (-1) in a random empty cell. Returns (-1,-1) if no space.
    std::pair<int,int> spawn_bomb();

    std::vector<std::pair<int,int>> empty_cells(const std::set<std::pair<int,int>>& excluded = {}) const;
    std::vector<std::pair<int,int>> occupied_numbered_cells(const std::set<std::pair<int,int>>& excluded = {}) const;

    // Row-major flat array of tile values for Python rendering
    std::vector<int> to_flat_values() const;

    // (row, col, passive_type_int) for each tile with a passive
    std::vector<std::tuple<int,int,int>> get_passive_map() const;

private:
    int rows_, cols_;
    std::vector<std::vector<Tile>> grid_;
    std::mt19937 rng_;
};
