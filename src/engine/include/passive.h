//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#pragma once

#include <string>

enum class PassiveType {
    NONE = 0,
    A_LITTLE_SLOW = 1,
    CONTRARIAN = 2,
};

// Bitmask check: returns true if 'stored' has the given flag bit set.
// Tiles can hold multiple passives simultaneously (e.g., A_LITTLE_SLOW | CONTRARIAN = 3).
inline bool has_passive(PassiveType stored, PassiveType flag) {
    return (static_cast<int>(stored) & static_cast<int>(flag)) != 0;
}

// Merge rule: a merged tile carries the OR of both source tiles' passives.
inline PassiveType combine_passives(PassiveType a, PassiveType b) {
    return static_cast<PassiveType>(static_cast<int>(a) | static_cast<int>(b));
}

std::string passive_name(PassiveType type);
std::string passive_description(PassiveType type);
