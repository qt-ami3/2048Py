import random as rand
import numpy as np

def newNum(grid):
    empty = list(zip(*np.where(grid == 0)))
    if empty:
        r, c = rand.choice(empty)
        grid[r][c] = 2
        return (r, c)  # Return position of new tile for animation
    return None

def newBomb(grid):
    """Spawn a bomb tile (-1) instead of a regular tile"""
    empty = list(zip(*np.where(grid == 0)))
    if empty:
        r, c = rand.choice(empty)
        grid[r][c] = -1  # -1 represents a bomb
        return (r, c)
    return None

def moveLeft(grid, r, c):
    moves = []  # Track tile movements for animation
    merges = []  # Track merges for animation
    
    for i in range(r):
        row = [(x, j) for j, x in enumerate(grid[i]) if x != 0]
        
        if not row:
            continue
            
        # Track original positions
        new_row = []
        
        j = 0
        target_col = 0
        while j < len(row):
            value, orig_col = row[j]
            
            # Check if current tile is a bomb
            if value == -1:
                # Bomb removes next tile it collides with
                if j < len(row) - 1:
                    # Remove both the bomb and the next tile
                    if orig_col != target_col:
                        moves.append((i, orig_col, i, target_col, value))
                    if row[j + 1][1] != target_col:
                        moves.append((i, row[j + 1][1], i, target_col, row[j + 1][0]))
                    # Don't add either tile to new_row (both are destroyed)
                    j += 2
                else:
                    # Bomb at end, just move it
                    new_row.append(value)
                    if orig_col != target_col:
                        moves.append((i, orig_col, i, target_col, value))
                    j += 1
                    target_col += 1
            # Check if next tile is a bomb
            elif j < len(row) - 1 and row[j + 1][0] == -1:
                # Regular tile collides with bomb, both destroyed
                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                if row[j + 1][1] != target_col:
                    moves.append((i, row[j + 1][1], i, target_col, row[j + 1][0]))
                j += 2
            # Check if we can merge with next tile (regular merge)
            elif j < len(row) - 1 and value == row[j + 1][0] and value > 0:
                new_value = value * 2
                new_row.append(new_value)
                
                # Track both tiles moving to merge position
                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                if row[j + 1][1] != target_col:
                    moves.append((i, row[j + 1][1], i, target_col, row[j + 1][0]))
                
                merges.append((i, target_col, new_value))
                j += 2
                target_col += 1
            else:
                new_row.append(value)
                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                j += 1
                target_col += 1
        
        # Update grid
        grid[i] = new_row + [0] * (c - len(new_row))
    
    return moves, merges

def moveRight(grid, r, c):
    moves = []
    merges = []
    
    for i in range(r):
        row = [(x, j) for j, x in enumerate(grid[i]) if x != 0]
        
        if not row:
            continue
        
        new_row = []
        
        j = len(row) - 1
        target_col = c - 1
        while j >= 0:
            value, orig_col = row[j]
            
            # Check if current tile is a bomb
            if value == -1:
                if j > 0:
                    # Remove both the bomb and the previous tile
                    if orig_col != target_col:
                        moves.append((i, orig_col, i, target_col, value))
                    if row[j - 1][1] != target_col:
                        moves.append((i, row[j - 1][1], i, target_col, row[j - 1][0]))
                    j -= 2
                else:
                    new_row.insert(0, value)
                    if orig_col != target_col:
                        moves.append((i, orig_col, i, target_col, value))
                    j -= 1
                    target_col -= 1
            # Check if previous tile is a bomb
            elif j > 0 and row[j - 1][0] == -1:
                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                if row[j - 1][1] != target_col:
                    moves.append((i, row[j - 1][1], i, target_col, row[j - 1][0]))
                j -= 2
            elif j > 0 and value == row[j - 1][0] and value > 0:
                new_value = value * 2
                new_row.insert(0, new_value)
                
                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                if row[j - 1][1] != target_col:
                    moves.append((i, row[j - 1][1], i, target_col, row[j - 1][0]))
                
                merges.append((i, target_col, new_value))
                j -= 2
                target_col -= 1
            else:
                new_row.insert(0, value)
                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                j -= 1
                target_col -= 1
        
        grid[i] = [0] * (c - len(new_row)) + new_row
    
    return moves, merges

def moveUp(grid, r, c):
    moves = []
    merges = []
    
    for col in range(c):
        column = [(grid[row][col], row) for row in range(r) if grid[row][col] != 0]
        
        if not column:
            continue
        
        new_column = []
        
        i = 0
        target_row = 0
        while i < len(column):
            value, orig_row = column[i]
            
            # Check if current tile is a bomb
            if value == -1:
                if i < len(column) - 1:
                    # Remove both the bomb and the next tile
                    if orig_row != target_row:
                        moves.append((orig_row, col, target_row, col, value))
                    if column[i + 1][1] != target_row:
                        moves.append((column[i + 1][1], col, target_row, col, column[i + 1][0]))
                    i += 2
                else:
                    new_column.append(value)
                    if orig_row != target_row:
                        moves.append((orig_row, col, target_row, col, value))
                    i += 1
                    target_row += 1
            # Check if next tile is a bomb
            elif i < len(column) - 1 and column[i + 1][0] == -1:
                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                if column[i + 1][1] != target_row:
                    moves.append((column[i + 1][1], col, target_row, col, column[i + 1][0]))
                i += 2
            elif i < len(column) - 1 and value == column[i + 1][0] and value > 0:
                new_value = value * 2
                new_column.append(new_value)
                
                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                if column[i + 1][1] != target_row:
                    moves.append((column[i + 1][1], col, target_row, col, column[i + 1][0]))
                
                merges.append((target_row, col, new_value))
                i += 2
                target_row += 1
            else:
                new_column.append(value)
                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                i += 1
                target_row += 1
        
        for row in range(r):
            grid[row][col] = new_column[row] if row < len(new_column) else 0
    
    return moves, merges

def moveDown(grid, r, c):
    moves = []
    merges = []
    
    for col in range(c):
        column = [(grid[row][col], row) for row in range(r) if grid[row][col] != 0]
        
        if not column:
            continue
        
        new_column = []
        
        i = len(column) - 1
        target_row = r - 1
        while i >= 0:
            value, orig_row = column[i]
            
            # Check if current tile is a bomb
            if value == -1:
                if i > 0:
                    # Remove both the bomb and the previous tile
                    if orig_row != target_row:
                        moves.append((orig_row, col, target_row, col, value))
                    if column[i - 1][1] != target_row:
                        moves.append((column[i - 1][1], col, target_row, col, column[i - 1][0]))
                    i -= 2
                else:
                    new_column.insert(0, value)
                    if orig_row != target_row:
                        moves.append((orig_row, col, target_row, col, value))
                    i -= 1
                    target_row -= 1
            # Check if previous tile is a bomb
            elif i > 0 and column[i - 1][0] == -1:
                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                if column[i - 1][1] != target_row:
                    moves.append((column[i - 1][1], col, target_row, col, column[i - 1][0]))
                i -= 2
            elif i > 0 and value == column[i - 1][0] and value > 0:
                new_value = value * 2
                new_column.insert(0, new_value)
                
                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                if column[i - 1][1] != target_row:
                    moves.append((column[i - 1][1], col, target_row, col, column[i - 1][0]))
                
                merges.append((target_row, col, new_value))
                i -= 2
                target_row -= 1
            else:
                new_column.insert(0, value)
                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                i -= 1
                target_row -= 1
        
        for row in range(r):
            grid[row][col] = (
                new_column[row - (r - len(new_column))] if row >= r - len(new_column) else 0
            )
    
    return moves, merges
