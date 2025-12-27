
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

            #print value
            value = playingGrid[row][col]
            
            if value:
                text_surface = font.render(str(value), True, "#eceff4")

                text_rect = text_surface.get_rect(
                    center=(x + square_size // 2, y + square_size // 2)
                )
                screen.blit(text_surface, text_rect)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

