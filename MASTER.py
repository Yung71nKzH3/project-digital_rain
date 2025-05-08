import pygame
import random

# Initialize Pygame
pygame.init()

# Screen dimensions
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Matrix Digital Rain")

# Font settings
font_size = 18
font = pygame.font.SysFont("consolas", font_size)

# Color
green = (0, 255, 0)
black = (0, 0, 0)

# Characters to use in the rain
characters = [chr(random.randint(33, 126)) for _ in range(94)] # Printable ASCII characters

# Raindrop properties
num_drops = screen_width // font_size
drops = []
for _ in range(num_drops):
    x = random.randint(0, screen_width - font_size)
    y = random.randint(-500, 0)
    length = random.randint(10, 25)
    speed = 2#random.randint(1, 5)
    drops.append([x, y, length, speed])

# Game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Draw background
    screen.fill(black)

    # Update and draw raindrops
    for i, drop in enumerate(drops):
        x, y, length, speed = drop

        # Draw each character in the drop
        for j in range(length):
            char = random.choice(characters)
            text = font.render(char, True, green)
            text_rect = text.get_rect(topleft=(x, y - j * font_size))
            screen.blit(text, text_rect)

        # Update drop position
        y += speed
        if y > screen_height:
            y = random.randint(-200, -50)
            length = random.randint(10, 25)
            speed = random.randint(5, 20)
        drops[i] = [x, y, length, speed]

    pygame.display.flip()

# Quit Pygame
pygame.quit()