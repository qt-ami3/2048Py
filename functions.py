import random as rand
import numpy as np

def newNum(grid):
    empty = list(zip(*np.where(grid == 0)))
    if empty:
        r, c = rand.choice(empty)
        grid[r][c] = 2

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
