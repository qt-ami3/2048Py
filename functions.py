import random as rand
import numpy as np

def newNum(grid):
    empty = list(zip(*np.where(grid == 0)))
    if empty:
        r, c = rand.choice(empty)
        grid[r][c] = 2

def moveLeft(grid, r, c):
    for i in range(r):
        row = [x for x in grid[i] if x != 0]

        j = 0
        while j < len(row) - 1:
            if row[j] == row[j + 1]:
                row[j] *= 2
                row[j + 1] = 0
                j += 1
            j += 1

        row = [x for x in row if x != 0]
        grid[i] = row + [0] * (c - len(row))

def moveRight(grid, r, c):
    for i in range(r):
        row = [x for x in grid[i] if x != 0]

        j = len(row) - 1
        while j > 0:
            if row[j] == row[j - 1]:
                row[j] *= 2
                row[j - 1] = 0
                j -= 1
            j -= 1

        row = [x for x in row if x != 0]

        grid[i] = [0] * (c - len(row)) + row

def moveUp(grid, r, c):
    for col in range(c):
        column = [grid[row][col] for row in range(r) if grid[row][col] != 0]

        i = 0
        while i < len(column) - 1:
            if column[i] == column[i + 1]:
                column[i] *= 2
                column[i + 1] = 0
                i += 1
            i += 1

        column = [x for x in column if x != 0]

        for row in range(r):
            grid[row][col] = column[row] if row < len(column) else 0

def moveDown(grid, r, c):
    for col in range(c):
        column = [grid[row][col] for row in range(r) if grid[row][col] != 0]

        i = len(column) - 1
        while i > 0:
            if column[i] == column[i - 1]:
                column[i] *= 2
                column[i - 1] = 0
                i -= 1
            i -= 1

        column = [x for x in column if x != 0]

        for row in range(r):
            grid[row][col] = (
                column[row - (r - len(column))] if row >= r - len(column) else 0
            )
