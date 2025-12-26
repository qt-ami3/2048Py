
import pygame
import numpy as np

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1200, 1200))
clock = pygame.time.Clock()
running = True

# ---- GRID CONFIG ----
square_size = 50
rows, cols = 4, 4

grid_width = cols * square_size
grid_height = rows * square_size

start_x = (screen.get_width() - grid_width) // 2
start_y = (screen.get_height() - grid_height) // 2
# ---------------------

playingGrid = np.array([
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0]
])

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill("#4c566a")

    for row in range(rows):
        for col in range(cols):
            x = start_x + col * square_size
            y = start_y + row * square_size

            pygame.draw.rect(
                screen,
                "#d8dee9",
                (x, y, square_size, square_size),
                2
            )

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

