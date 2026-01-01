
import pygame
import random as rand
import numpy as np

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1200, 1200))
clock = pygame.time.Clock()
running = True

font = pygame.font.SysFont("fonts/MapleMono-NF-Base.ttf", 48)

#grid config
square_size = 100
rows, cols = 4, 4

grid_width = cols * square_size
grid_height = rows * square_size

start_x = (screen.get_width() - grid_width) // 2
start_y = (screen.get_height() - grid_height) // 2

playingGrid = np.array([
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0]
])

playingGrid[rand.randint(0,3)][rand.randint(0,3)] = 2
playingGrid[rand.randint(0,3)][rand.randint(0,3)] = 2

def newNum(grid):
    empty = list(zip(*np.where(grid == 0)))
    if empty:
        r, c = rand.choice(empty)
        grid[r][c] = 2

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            match event.key:
                case pygame.K_UP | pygame.K_DOWN | pygame.K_LEFT | pygame.K_RIGHT:
                    newNum(playingGrid)

    screen.fill("#4c566a")

    for r in range(rows):
        for c in range(cols):
            x = start_x + c * square_size
            y = start_y + r * square_size

            pygame.draw.rect(screen, "#d8dee9", (x, y, square_size, square_size), 2)

            value = playingGrid[r][c]
            if value:
                text = font.render(str(value), True, "#eceff4")
                rect = text.get_rect(center=(x + square_size//2, y + square_size//2))
                screen.blit(text, rect)

    pygame.display.flip()
    clock.tick(60)
