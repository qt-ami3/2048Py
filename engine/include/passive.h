#pragma once

#include <string>

enum class PassiveType {
    NONE = 0,
    A_LITTLE_SLOW = 1,
};

std::string passive_name(PassiveType type);
std::string passive_description(PassiveType type);
