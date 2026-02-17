//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#pragma once

#include "passive.h"

struct Tile {
    int value = 0;
    PassiveType passive = PassiveType::NONE;

    bool is_empty() const { return value == 0; }
    bool is_bomb() const { return value == -1; }
    bool is_snail() const { return value == -2; }
    bool is_numbered() const { return value > 0; }
    bool has_passive() const { return passive != PassiveType::NONE; }
};
