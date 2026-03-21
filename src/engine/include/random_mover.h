//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#pragma once

struct RandomMoverState {
    int row, col;
};

struct RandomMoverUpdate {
    int old_row, old_col;
    int new_row, new_col;
};
