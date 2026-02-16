//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#include "board.h"
#include <algorithm>
#include <stdexcept>

Board::Board(int rows, int cols)
    : rows_(rows), cols_(cols),
      grid_(rows, std::vector<Tile>(cols)),
      rng_(std::random_device{}())
{
}

Tile& Board::at(int r, int c) {
    return grid_[r][c];
}

const Tile& Board::at(int r, int c) const {
    return grid_[r][c];
}

void Board::expand(const std::string& direction) {
    if (direction == "down") {
        rows_++;
        grid_.emplace_back(cols_);
    } else if (direction == "up") {
        rows_++;
        grid_.insert(grid_.begin(), std::vector<Tile>(cols_));
    } else if (direction == "right") {
        cols_++;
        for (auto& row : grid_) {
            row.emplace_back();
        }
    } else if (direction == "left") {
        cols_++;
        for (auto& row : grid_) {
            row.insert(row.begin(), Tile{});
        }
    }
}

std::pair<int,int> Board::spawn_number(const std::set<std::pair<int,int>>& excluded) {
    auto empties = empty_cells(excluded);
    if (empties.empty()) return {-1, -1};

    std::uniform_int_distribution<int> dist(0, (int)empties.size() - 1);
    auto [r, c] = empties[dist(rng_)];
    grid_[r][c].value = 1024;
    grid_[r][c].passive = PassiveType::NONE;
    return {r, c};
}

std::pair<int,int> Board::spawn_bomb() {
    auto empties = empty_cells();
    if (empties.empty()) return {-1, -1};

    std::uniform_int_distribution<int> dist(0, (int)empties.size() - 1);
    auto [r, c] = empties[dist(rng_)];
    grid_[r][c].value = -1;
    grid_[r][c].passive = PassiveType::NONE;
    return {r, c};
}

std::vector<std::pair<int,int>> Board::empty_cells(const std::set<std::pair<int,int>>& excluded) const {
    std::vector<std::pair<int,int>> result;
    for (int r = 0; r < rows_; r++) {
        for (int c = 0; c < cols_; c++) {
            if (grid_[r][c].is_empty() && excluded.find({r, c}) == excluded.end()) {
                result.push_back({r, c});
            }
        }
    }
    return result;
}

std::vector<std::pair<int,int>> Board::occupied_numbered_cells(const std::set<std::pair<int,int>>& excluded) const {
    std::vector<std::pair<int,int>> result;
    for (int r = 0; r < rows_; r++) {
        for (int c = 0; c < cols_; c++) {
            if (grid_[r][c].is_numbered() && excluded.find({r, c}) == excluded.end()) {
                result.push_back({r, c});
            }
        }
    }
    return result;
}

std::vector<int> Board::to_flat_values() const {
    std::vector<int> result;
    result.reserve(rows_ * cols_);
    for (int r = 0; r < rows_; r++) {
        for (int c = 0; c < cols_; c++) {
            result.push_back(grid_[r][c].value);
        }
    }
    return result;
}

std::vector<std::tuple<int,int,int>> Board::get_passive_map() const {
    std::vector<std::tuple<int,int,int>> result;
    for (int r = 0; r < rows_; r++) {
        for (int c = 0; c < cols_; c++) {
            if (grid_[r][c].has_passive()) {
                result.push_back({r, c, static_cast<int>(grid_[r][c].passive)});
            }
        }
    }
    return result;
}
