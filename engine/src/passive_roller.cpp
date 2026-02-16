//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#include "passive_roller.h"
#include <algorithm>

PassiveRoller::PassiveRoller()
    : rng_(std::random_device{}())
{
}

std::vector<PassiveCandidate> PassiveRoller::roll(
    const Board& board,
    const std::vector<MergeInfo>& merges,
    const std::set<std::pair<int,int>>& excluded_positions)
{
    std::vector<PassiveCandidate> candidates;

    // Get all eligible tiles (occupied, numbered, not excluded)
    auto eligible = board.occupied_numbered_cells(excluded_positions);
    if (eligible.empty()) return candidates;

    for (const auto& merge : merges) {
        double chance = merge.new_value * 0.1;  // e.g., 2+2=4 -> 0.4%

        // Determine number of picks
        int guaranteed = static_cast<int>(chance / 100.0);
        double remainder = chance - (guaranteed * 100.0);

        int num_picks = guaranteed;

        // Roll for the remainder
        if (remainder > 0.0) {
            std::uniform_real_distribution<double> dist(0.0, 100.0);
            if (dist(rng_) < remainder) {
                num_picks++;
            }
        }

        // Only one passive per turn: if this roll succeeds, pick one tile and stop
        if (num_picks > 0 && !eligible.empty()) {
            std::uniform_int_distribution<int> tile_dist(0, (int)eligible.size() - 1);
            int idx = tile_dist(rng_);
            auto [r, c] = eligible[idx];

            if (board.at(r, c).is_numbered()) {
                candidates.push_back({r, c, board.at(r, c).value});
                return candidates;  // Stop rolling after first success
            }
        }
    }

    return candidates;
}
