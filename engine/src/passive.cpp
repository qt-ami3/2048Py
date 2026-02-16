//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#include "passive.h"

std::string passive_name(PassiveType type) {
    switch (type) {
        case PassiveType::A_LITTLE_SLOW: return "A Little Slow";
        default: return "None";
    }
}

std::string passive_description(PassiveType type) {
    switch (type) {
        case PassiveType::A_LITTLE_SLOW:
            return "Tile moves one cell per turn along its path instead of instantly.";
        default: return "";
    }
}
