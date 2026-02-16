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
};

std::string passive_name(PassiveType type);
std::string passive_description(PassiveType type);
