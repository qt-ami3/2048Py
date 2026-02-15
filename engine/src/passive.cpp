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
