#   shaders from libretro/gist-shaders

import pygame
import random as rand
import numpy as np
import functions as func
import moderngl
import array

# pygame setup
pygame.init()

# Native monitor resolution (fullscreen) / display resolution
NATIVE_WIDTH = 1920
NATIVE_HEIGHT = 1200

# Render resolution (lower for performance)
RENDER_WIDTH = 3840
RENDER_HEIGHT = 2400

# Windowed resolution (smaller for windowed mode)
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

# Fullscreen state
is_fullscreen = True

# Create display based on initial mode with OpenGL support
if is_fullscreen:
    screen = pygame.display.set_mode((NATIVE_WIDTH, NATIVE_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN)
    display_width, display_height = NATIVE_WIDTH, NATIVE_HEIGHT
else:
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
    display_width, display_height = WINDOW_WIDTH, WINDOW_HEIGHT

# Initialize ModernGL
ctx = moderngl.create_context()

# Create render surface at lower resolution
render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))

# Use render surface dimensions for game logic
screen_width = RENDER_WIDTH
screen_height = RENDER_HEIGHT

clock = pygame.time.Clock()
running = True

pygame.font.init()
font = pygame.font.Font("fonts/pixelOperatorBold.ttf", 29)
small_font = pygame.font.Font("fonts/pixelOperatorBold.ttf", 20)

# Grid config
square_size = 100
rows, cols = 4, 4

grid_width = cols * square_size
grid_height = rows * square_size

start_x = (RENDER_WIDTH - grid_width) // 2
start_y = (RENDER_HEIGHT - grid_height) // 2

playingGrid = np.zeros((rows, cols), dtype=int)

func.newNum(playingGrid)
func.newNum(playingGrid)

playingGridLast = playingGrid.copy()

# Score tracking - start with initial tiles
points = sum(sum(playingGrid))

# Ability system
bomb_ability_cost = 750
bomb_ability_active = False
next_tile_is_bomb = False
selecting_bomb_position = False
hovered_tile = None
bomb_image = None
try:
    bomb_image = pygame.image.load("assets/sprites/bomb.png")
    bomb_image = pygame.transform.scale(bomb_image, (80, 80))
except:
    print("Warning: Could not load bomb.png")

# Menu configuration
menu_height = 150
menu_y = start_y + grid_height + 30
button_width = 200
button_height = 60
button_x = start_x + (grid_width - button_width) // 2

# Animation variables
animating = False
animation_progress = 0
animation_speed = 0.15
moving_tiles = []
merging_tiles = []
new_tile_pos = None
new_tile_scale = 0

# Grid expansion animation
grid_expanding = False
expand_progress = 0
expand_speed = 0.03
pending_expand = False
expand_old_rows = 0
expand_old_cols = 0
expand_old_sx = 0
expand_old_sy = 0
expand_direction = ""

# Color scheme
COLORS = {
    0: "#4c566a",
    2: "#88c0d0",
    4: "#81a1c1",
    8: "#5e81ac",
    16: "#bf616a",
    32: "#d08770",
    64: "#ebcb8b",
    128: "#a3be8c",
    256: "#b48ead",
    512: "#8fbcbb",
    1024: "#5e81ac",
    2048: "#bf616a",
    -1: "#bf616a",
}

# CRT Shader parameters
crt_params = {
    'hardScan': -10.0,  # Very pronounced scanlines (like arcade CRT)
    'hardPix': 0.7,  # Sharper pixels
    'warpX': 0.12,  # More screen curvature
    'warpY': 0.14,
    'maskDark': 0.3,  # Much darker mask (was 0.5)
    'maskLight': 1.8,  # Brighter phosphors (was 1.5)
    'shadowMask': 0.0,  # VGA-style RGB triads
    'brightBoost': 1.1,  # Higher brightness to compensate
    'hardBloomPix': -1.5,
    'hardBloomScan': -2.0,
    'bloomAmount': 0.20,  # More bloom/glow
    'shape': 2.0
}

# Setup ModernGL shader
vertex_shader = '''
#version 330

in vec2 in_vert;
in vec2 in_texcoord;
out vec2 v_texcoord;

void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
    v_texcoord = in_texcoord;
}
'''

fragment_shader = '''
#version 330

uniform sampler2D Texture;
uniform vec2 TextureSize;
uniform vec2 InputSize;

uniform float hardScan;
uniform float hardPix;
uniform float warpX;
uniform float warpY;
uniform float maskDark;
uniform float maskLight;
uniform float shadowMask;
uniform float brightBoost;
uniform float hardBloomPix;
uniform float hardBloomScan;
uniform float bloomAmount;
uniform float shape;

in vec2 v_texcoord;
out vec4 FragColor;

#define SourceSize vec4(TextureSize, 1.0 / TextureSize)

float ToLinear1(float c) {
    return (c <= 0.04045) ? c / 12.92 : pow((c + 0.055) / 1.055, 2.4);
}

vec3 ToLinear(vec3 c) {
    return vec3(ToLinear1(c.r), ToLinear1(c.g), ToLinear1(c.b));
}

float ToSrgb1(float c) {
    return (c < 0.0031308 ? c * 12.92 : 1.055 * pow(c, 0.41666) - 0.055);
}

vec3 ToSrgb(vec3 c) {
    return vec3(ToSrgb1(c.r), ToSrgb1(c.g), ToSrgb1(c.b));
}

vec3 Fetch(vec2 pos, vec2 off) {
    pos = (floor(pos * SourceSize.xy + off) + vec2(0.5, 0.5)) / SourceSize.xy;
    return ToLinear(brightBoost * texture(Texture, pos.xy).rgb);
}

vec2 Dist(vec2 pos) {
    pos = pos * SourceSize.xy;
    return -((pos - floor(pos)) - vec2(0.5));
}

float Gaus(float pos, float scale) {
    return exp2(scale * pow(abs(pos), shape));
}

vec3 Horz3(vec2 pos, float off) {
    vec3 b = Fetch(pos, vec2(-1.0, off));
    vec3 c = Fetch(pos, vec2(0.0, off));
    vec3 d = Fetch(pos, vec2(1.0, off));
    float dst = Dist(pos).x;
    float scale = hardPix;
    float wb = Gaus(dst - 1.0, scale);
    float wc = Gaus(dst + 0.0, scale);
    float wd = Gaus(dst + 1.0, scale);
    return (b * wb + c * wc + d * wd) / (wb + wc + wd);
}

vec3 Horz5(vec2 pos, float off) {
    vec3 a = Fetch(pos, vec2(-2.0, off));
    vec3 b = Fetch(pos, vec2(-1.0, off));
    vec3 c = Fetch(pos, vec2(0.0, off));
    vec3 d = Fetch(pos, vec2(1.0, off));
    vec3 e = Fetch(pos, vec2(2.0, off));
    float dst = Dist(pos).x;
    float scale = hardPix;
    float wa = Gaus(dst - 2.0, scale);
    float wb = Gaus(dst - 1.0, scale);
    float wc = Gaus(dst + 0.0, scale);
    float wd = Gaus(dst + 1.0, scale);
    float we = Gaus(dst + 2.0, scale);
    return (a * wa + b * wb + c * wc + d * wd + e * we) / (wa + wb + wc + wd + we);
}

vec3 Horz7(vec2 pos, float off) {
    vec3 a = Fetch(pos, vec2(-3.0, off));
    vec3 b = Fetch(pos, vec2(-2.0, off));
    vec3 c = Fetch(pos, vec2(-1.0, off));
    vec3 d = Fetch(pos, vec2(0.0, off));
    vec3 e = Fetch(pos, vec2(1.0, off));
    vec3 f = Fetch(pos, vec2(2.0, off));
    vec3 g = Fetch(pos, vec2(3.0, off));
    float dst = Dist(pos).x;
    float scale = hardBloomPix;
    float wa = Gaus(dst - 3.0, scale);
    float wb = Gaus(dst - 2.0, scale);
    float wc = Gaus(dst - 1.0, scale);
    float wd = Gaus(dst + 0.0, scale);
    float we = Gaus(dst + 1.0, scale);
    float wf = Gaus(dst + 2.0, scale);
    float wg = Gaus(dst + 3.0, scale);
    return (a * wa + b * wb + c * wc + d * wd + e * we + f * wf + g * wg) / (wa + wb + wc + wd + we + wf + wg);
}

float Scan(vec2 pos, float off) {
    float dst = Dist(pos).y;
    return Gaus(dst + off, hardScan);
}

float BloomScan(vec2 pos, float off) {
    float dst = Dist(pos).y;
    return Gaus(dst + off, hardBloomScan);
}

vec3 Tri(vec2 pos) {
    vec3 a = Horz3(pos, -1.0);
    vec3 b = Horz5(pos, 0.0);
    vec3 c = Horz3(pos, 1.0);
    float wa = Scan(pos, -1.0);
    float wb = Scan(pos, 0.0);
    float wc = Scan(pos, 1.0);
    return (a * wa + b * wb + c * wc) / (wa + wb + wc);
}

vec3 Bloom(vec2 pos) {
    vec3 a = Horz5(pos, -2.0);
    vec3 b = Horz7(pos, -1.0);
    vec3 c = Horz7(pos, 0.0);
    vec3 d = Horz7(pos, 1.0);
    vec3 e = Horz5(pos, 2.0);
    float wa = BloomScan(pos, -2.0);
    float wb = BloomScan(pos, -1.0);
    float wc = BloomScan(pos, 0.0);
    float wd = BloomScan(pos, 1.0);
    float we = BloomScan(pos, 2.0);
    return a * wa + b * wb + c * wc + d * wd + e * we;
}

vec2 Warp(vec2 pos) {
    pos = pos * 2.0 - 1.0;
    pos *= vec2(1.0 + (pos.y * pos.y) * warpX, 1.0 + (pos.x * pos.x) * warpY);
    return pos * 0.5 + 0.5;
}

vec3 Mask(vec2 pos) {
    vec3 mask = vec3(maskDark, maskDark, maskDark);
    
    // Aperture-grille (vertical RGB stripes - like Trinitron)
    if (shadowMask == 2.0) {
        pos.x = fract(pos.x * 0.333333333);
        if (pos.x < 0.333) mask.r = maskLight;
        else if (pos.x < 0.666) mask.g = maskLight;
        else mask.b = maskLight;
    }
    // Stretched VGA style shadow mask (diagonal RGB pattern)
    else if (shadowMask == 3.0) {
        pos.x += pos.y * 3.0;
        pos.x = fract(pos.x * 0.166666666);
        if (pos.x < 0.333) mask.r = maskLight;
        else if (pos.x < 0.666) mask.g = maskLight;
        else mask.b = maskLight;
    }
    // VGA style shadow mask (grid pattern)
    else if (shadowMask == 4.0) {
        pos.xy = floor(pos.xy * vec2(1.0, 0.5));
        pos.x += pos.y * 3.0;
        pos.x = fract(pos.x * 0.166666666);
        if (pos.x < 0.333) mask.r = maskLight;
        else if (pos.x < 0.666) mask.g = maskLight;
        else mask.b = maskLight;
    }
    
    return mask;
}

void main() {
    vec2 pos = Warp(v_texcoord * (TextureSize / InputSize)) * (InputSize / TextureSize);
    vec3 outColor = Tri(pos);
    outColor.rgb += Bloom(pos) * bloomAmount;
    
    if (shadowMask > 0.0)
        outColor.rgb *= Mask(gl_FragCoord.xy * 1.000001);

    // Horizontal scanlines - 2px dark / 2px bright bands
    float sl = step(2.0, mod(gl_FragCoord.y, 4.0));
    outColor.rgb *= mix(0.5, 1.0, sl);

    FragColor = vec4(ToSrgb(outColor.rgb), 1.0);
}
'''

# Create shader program
prog = ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

# Create fullscreen quad
vertices = np.array([
    -1.0, -1.0,  0.0, 0.0,
    1.0, -1.0,  1.0, 0.0,
    -1.0,  1.0,  0.0, 1.0,
    1.0,  1.0,  1.0, 1.0,
], dtype='f4')

vbo = ctx.buffer(vertices.tobytes())
vao = ctx.simple_vertex_array(prog, vbo, 'in_vert', 'in_texcoord')

# Create texture for pygame surface
texture = ctx.texture((RENDER_WIDTH, RENDER_HEIGHT), 3)
texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
texture.repeat_x = False
texture.repeat_y = False

# Setup framebuffer for rendering
fbo = ctx.framebuffer(color_attachments=[ctx.texture((display_width, display_height), 4)])

def get_tile_color(value):
    return COLORS.get(value, "#2e3440")

def lerp(start, end, t):
    return start + (end - start) * t

def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)

# Pre-rendered tile surface cache
tile_cache = {}

def init_tile_cache():
    for value in list(COLORS.keys()):
        if value == 0:
            continue
        surface = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
        color = pygame.Color(get_tile_color(value))
        pygame.draw.rect(surface, color, (0, 0, square_size, square_size))
        pygame.draw.rect(surface, "#d8dee9", (0, 0, square_size, square_size), 2)
        if value == -1 and bomb_image:
            bomb_scaled = pygame.transform.scale(bomb_image, (int(square_size * 0.8), int(square_size * 0.8)))
            bomb_rect = bomb_scaled.get_rect(center=(square_size // 2, square_size // 2))
            surface.blit(bomb_scaled, bomb_rect)
        else:
            text = font.render(str(value), True, "#eceff4")
            text_rect = text.get_rect(center=(square_size // 2, square_size // 2))
            surface.blit(text, text_rect)
        tile_cache[value] = surface

init_tile_cache()

# Score text cache
_score_cache = {'text': None, 'surface': None}

def get_cached_score(score_value):
    text = f"Score: {score_value}"
    if _score_cache['text'] != text:
        _score_cache['text'] = text
        _score_cache['surface'] = font.render(text, True, "#eceff4")
    return _score_cache['surface']

def prepare_tile_surface(value, scale):
    """Create a scaled tile surface - safe for thread pool execution"""
    if scale == 1.0 and value in tile_cache:
        return tile_cache[value]
    scaled_size = max(int(square_size * scale), 1)
    if value in tile_cache:
        return pygame.transform.smoothscale(tile_cache[value], (scaled_size, scaled_size))
    surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
    color = pygame.Color(get_tile_color(value))
    pygame.draw.rect(surface, color, (0, 0, scaled_size, scaled_size))
    pygame.draw.rect(surface, "#d8dee9", (0, 0, scaled_size, scaled_size), 2)
    if value == -1 and bomb_image:
        bsz = int(scaled_size * 0.8)
        bomb_s = pygame.transform.scale(bomb_image, (bsz, bsz))
        bomb_r = bomb_s.get_rect(center=(scaled_size // 2, scaled_size // 2))
        surface.blit(bomb_s, bomb_r)
    elif value != 0:
        text = font.render(str(value), True, "#eceff4")
        text_r = text.get_rect(center=(scaled_size // 2, scaled_size // 2))
        surface.blit(text, text_r)
    return surface

def toggle_fullscreen():
    global is_fullscreen, screen, display_width, display_height, ctx, fbo
    
    is_fullscreen = not is_fullscreen
    
    if is_fullscreen:
        screen = pygame.display.set_mode((NATIVE_WIDTH, NATIVE_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN)
        display_width, display_height = NATIVE_WIDTH, NATIVE_HEIGHT
    else:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
        display_width, display_height = WINDOW_WIDTH, WINDOW_HEIGHT
    
    # Recreate context and framebuffer for new resolution
    ctx = moderngl.create_context()
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((display_width, display_height), 4)])

def start_grid_expansion():
    global rows, cols, playingGrid, playingGridLast, grid_width, grid_height
    global start_x, start_y, menu_y, button_x
    global grid_expanding, expand_progress, expand_old_rows, expand_old_cols
    global expand_old_sx, expand_old_sy, expand_direction

    expand_old_sx = start_x
    expand_old_sy = start_y
    expand_old_rows = rows
    expand_old_cols = cols

    expand_direction = rand.choice(["up", "down", "left", "right"])

    if expand_direction in ("up", "down"):
        rows += 1
    else:
        cols += 1

    new_grid = np.zeros((rows, cols), dtype=int)

    if expand_direction == "down":
        new_grid[:expand_old_rows, :expand_old_cols] = playingGrid
    elif expand_direction == "up":
        new_grid[1:, :expand_old_cols] = playingGrid
    elif expand_direction == "right":
        new_grid[:expand_old_rows, :expand_old_cols] = playingGrid
    elif expand_direction == "left":
        new_grid[:expand_old_rows, 1:] = playingGrid

    playingGrid = new_grid
    playingGridLast = playingGrid.copy()

    grid_width = cols * square_size
    grid_height = rows * square_size
    start_x = (RENDER_WIDTH - grid_width) // 2
    start_y = (RENDER_HEIGHT - grid_height) // 2
    menu_y = start_y + grid_height + 30
    button_x = start_x + (grid_width - button_width) // 2

    grid_expanding = True
    expand_progress = 0

    print(f"Grid expanded to {rows}x{cols}! (direction: {expand_direction})")

def process_move(direction):
    global playingGrid, playingGridLast, animating, moving_tiles, merging_tiles
    global animation_progress, new_tile_pos, new_tile_scale, points, next_tile_is_bomb, pending_expand
    
    if animating:
        return
    
    grid_before = playingGrid.copy()
    
    if direction == "up":
        moves, merges = func.moveUp(playingGrid, rows, cols)
    elif direction == "down":
        moves, merges = func.moveDown(playingGrid, rows, cols)
    elif direction == "left":
        moves, merges = func.moveLeft(playingGrid, rows, cols)
    elif direction == "right":
        moves, merges = func.moveRight(playingGrid, rows, cols)
    
    if np.array_equal(grid_before, playingGrid):
        return
    
    points_gained = sum(value for _, _, value in merges)
    
    if moves or merges:
        animating = True
        animation_progress = 0
        moving_tiles = [(sr, sc, er, ec, val, 0) for sr, sc, er, ec, val in moves]
        merging_tiles = [(r, c, val, 1.0) for r, c, val in merges]
        
        new_pos = func.newNum(playingGrid)
        
        if new_pos:
            new_tile_pos = new_pos
            new_tile_scale = 0
            r, c = new_pos
            if playingGrid[r][c] > 0:
                points_gained += playingGrid[r][c]
        
        points += points_gained

        # Check if any merge created a 2048 tile
        if any(val == 2048 for _, _, val in merges):
            pending_expand = True

        playingGridLast = playingGrid.copy()
        print()
        print(f"Score: {points} (+{points_gained})")

def update_animations(dt):
    global animating, animation_progress, moving_tiles, merging_tiles, new_tile_scale, new_tile_pos
    global grid_expanding, expand_progress, pending_expand

    # Update grid expansion animation
    if grid_expanding:
        expand_progress += expand_speed
        if expand_progress >= 1.0:
            grid_expanding = False
            expand_progress = 0
        return

    if not animating:
        return
    
    animation_progress += animation_speed
    
    eased_progress = ease_out_cubic(min(animation_progress, 1.0))
    moving_tiles = [(sr, sc, er, ec, val, eased_progress) for sr, sc, er, ec, val, _ in moving_tiles]
    
    if animation_progress > 0.6:
        merge_progress = (animation_progress - 0.6) / 0.4
        for i, (r, c, val, _) in enumerate(merging_tiles):
            if merge_progress < 0.5:
                scale = 1.0 + merge_progress * 0.4
            else:
                scale = 1.2 - (merge_progress - 0.5) * 0.4
            merging_tiles[i] = (r, c, val, scale)
    
    if new_tile_pos and animation_progress > 0.7:
        new_tile_scale = min((animation_progress - 0.7) / 0.3, 1.0)
    
    if animation_progress >= 1.0:
        animating = False
        moving_tiles = []
        merging_tiles = []
        new_tile_pos = None
        new_tile_scale = 0
        if pending_expand:
            pending_expand = False
            start_grid_expansion()

def draw_tile(r, c, value, scale=1.0, alpha=255):
    x = start_x + c * square_size
    y = start_y + r * square_size

    # Fast path: blit directly from cache for standard tiles
    if scale == 1.0 and alpha == 255 and value in tile_cache:
        render_surface.blit(tile_cache[value], (x, y))
        return

    scaled_size = max(int(square_size * scale), 1)
    offset = (square_size - scaled_size) / 2

    if value in tile_cache:
        tile_surface = pygame.transform.smoothscale(tile_cache[value], (scaled_size, scaled_size))
    else:
        tile_surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
        color = pygame.Color(get_tile_color(value))
        color.a = alpha
        pygame.draw.rect(tile_surface, color, (0, 0, scaled_size, scaled_size))
        pygame.draw.rect(tile_surface, "#d8dee9", (0, 0, scaled_size, scaled_size), 2)
        if value == -1 and bomb_image:
            bomb_scaled = pygame.transform.scale(bomb_image, (int(scaled_size * 0.8), int(scaled_size * 0.8)))
            bomb_rect = bomb_scaled.get_rect(center=(scaled_size // 2, scaled_size // 2))
            tile_surface.blit(bomb_scaled, bomb_rect)
        elif value != 0:
            text = font.render(str(value), True, "#eceff4")
            text_rect = text.get_rect(center=(scaled_size // 2, scaled_size // 2))
            tile_surface.blit(text, text_rect)

    if alpha != 255:
        tile_surface.set_alpha(alpha)

    render_surface.blit(tile_surface, (x + offset, y + offset))

def draw_button(x, y, width, height, text, cost, can_afford, active=False):
    if can_afford and not active:
        color = "#88c0d0"
        hover_color = "#81a1c1"
    elif active:
        color = "#a3be8c"
        hover_color = "#a3be8c"
    else:
        color = "#4c566a"
        hover_color = "#4c566a"
    
    mouse_pos = pygame.mouse.get_pos()
    mouse_x = mouse_pos[0] * RENDER_WIDTH / display_width
    mouse_y = mouse_pos[1] * RENDER_HEIGHT / display_height
    
    is_hover = x <= mouse_x <= x + width and y <= mouse_y <= y + height
    
    button_color = hover_color if is_hover else color
    
    pygame.draw.rect(render_surface, button_color, (x, y, width, height))
    pygame.draw.rect(render_surface, "#d8dee9", (x, y, width, height), 3)
    
    if active:
        button_text = small_font.render("ACTIVE", True, "#eceff4")
    else:
        button_text = small_font.render(text, True, "#eceff4")
    text_rect = button_text.get_rect(center=(x + width//2, y + height//3))
    render_surface.blit(button_text, text_rect)
    
    if not active:
        cost_color = "#a3be8c" if can_afford else "#bf616a"
        cost_text = small_font.render(f"Cost: {cost}", True, cost_color)
        cost_rect = cost_text.get_rect(center=(x + width//2, y + 2*height//3))
        render_surface.blit(cost_text, cost_rect)
    
    return is_hover and can_afford and not active

def handle_button_click(mouse_pos):
    global points, next_tile_is_bomb, selecting_bomb_position
    
    mouse_x = mouse_pos[0] * RENDER_WIDTH / display_width
    mouse_y = mouse_pos[1] * RENDER_HEIGHT / display_height
    
    button_y = menu_y + 30
    if button_x <= mouse_x <= button_x + button_width and button_y <= mouse_y <= button_y + button_height:
        if points >= bomb_ability_cost and not selecting_bomb_position:
            points -= bomb_ability_cost
            selecting_bomb_position = True
            print(f"Bomb ability activated! Click an empty tile to place the bomb. Score: {points}")

def get_tile_from_mouse(mouse_pos):
    mouse_x = mouse_pos[0] * RENDER_WIDTH / display_width
    mouse_y = mouse_pos[1] * RENDER_HEIGHT / display_height
    
    if start_x <= mouse_x <= start_x + grid_width and start_y <= mouse_y <= start_y + grid_height:
        c = int((mouse_x - start_x) // square_size)
        r = int((mouse_y - start_y) // square_size)
        
        if 0 <= r < rows and 0 <= c < cols:
            return (r, c)
    
    return None

def place_bomb_at_tile(r, c):
    global playingGrid, selecting_bomb_position, animating, new_tile_pos, new_tile_scale, animation_progress
    
    if playingGrid[r][c] == 0:
        playingGrid[r][c] = -1
        selecting_bomb_position = False
        
        animating = True
        animation_progress = 0.7
        new_tile_pos = (r, c)
        new_tile_scale = 0
        
        print(f"Bomb placed at position ({r}, {c})")

def render_to_opengl():
    """Convert pygame surface to OpenGL texture and render with CRT shader"""
    # Convert surface to texture data
    texture_data = pygame.image.tostring(render_surface, 'RGB', True)

    # Update shader uniforms
    prog['TextureSize'].value = (RENDER_WIDTH, RENDER_HEIGHT)
    prog['InputSize'].value = (RENDER_WIDTH, RENDER_HEIGHT)
    prog['hardScan'].value = crt_params['hardScan']
    prog['hardPix'].value = crt_params['hardPix']
    prog['warpX'].value = crt_params['warpX']
    prog['warpY'].value = crt_params['warpY']
    prog['maskDark'].value = crt_params['maskDark']
    prog['maskLight'].value = crt_params['maskLight']
    prog['shadowMask'].value = crt_params['shadowMask']
    prog['brightBoost'].value = crt_params['brightBoost']
    prog['hardBloomPix'].value = crt_params['hardBloomPix']
    prog['hardBloomScan'].value = crt_params['hardBloomScan']
    prog['bloomAmount'].value = crt_params['bloomAmount']
    prog['shape'].value = crt_params['shape']

    # Upload texture data
    texture.write(texture_data)

    # Render
    ctx.clear(0.0, 0.0, 0.0)
    texture.use(0)
    prog['Texture'].value = 0
    vao.render(moderngl.TRIANGLE_STRIP)

while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN and not animating and not grid_expanding:
            match event.key:
                case pygame.K_UP: 
                    process_move("up")
                case pygame.K_DOWN:
                    process_move("down")
                case pygame.K_LEFT:
                    process_move("left")
                case pygame.K_RIGHT:
                    process_move("right")
                case pygame.K_ESCAPE:
                    if selecting_bomb_position:
                        selecting_bomb_position = False
                        points += bomb_ability_cost
                        print("Bomb placement cancelled. Points refunded.")
                    else:
                        running = False
                case pygame.K_F11:
                    toggle_fullscreen()
        
        if event.type == pygame.MOUSEMOTION:
            if selecting_bomb_position:
                hovered_tile = get_tile_from_mouse(event.pos)
        
        if event.type == pygame.MOUSEBUTTONDOWN and not animating and not grid_expanding:
            if event.button == 1:
                if selecting_bomb_position:
                    tile = get_tile_from_mouse(event.pos)
                    if tile:
                        r, c = tile
                        place_bomb_at_tile(r, c)
                else:
                    handle_button_click(event.pos)

    update_animations(dt)

    # Draw to pygame surface
    render_surface.fill("#4c566a")
    
    # Draw score (cached - only re-renders when score changes)
    score_text = get_cached_score(points)
    render_surface.blit(score_text, (50, 50))

    # Temporarily override start positions for expansion animation
    _expand_real_sx, _expand_real_sy = start_x, start_y
    if grid_expanding:
        t = ease_out_cubic(expand_progress)
        start_x = int(lerp(expand_old_sx, _expand_real_sx, t))
        start_y = int(lerp(expand_old_sy, _expand_real_sy, t))

    for r in range(rows):
        for c in range(cols):
            x = start_x + c * square_size
            y = start_y + r * square_size

            if grid_expanding:
                if expand_direction == "down":
                    is_new_cell = r >= expand_old_rows
                elif expand_direction == "up":
                    is_new_cell = r == 0
                elif expand_direction == "right":
                    is_new_cell = c >= expand_old_cols
                elif expand_direction == "left":
                    is_new_cell = c == 0
                else:
                    is_new_cell = False
            else:
                is_new_cell = False

            if selecting_bomb_position and hovered_tile == (r, c) and playingGrid[r][c] == 0:
                pygame.draw.rect(render_surface, "#a3be8c", (x, y, square_size, square_size))
                pygame.draw.rect(render_surface, "#d8dee9", (x, y, square_size, square_size), 4)
            elif is_new_cell:
                # New cell stretches/fades in during expansion
                alpha = int(255 * ease_out_cubic(expand_progress))
                cell_scale = ease_out_cubic(expand_progress)
                scaled = max(int(square_size * cell_scale), 1)
                off = (square_size - scaled) // 2
                cell_surf = pygame.Surface((scaled, scaled), pygame.SRCALPHA)
                border_color = pygame.Color("#d8dee9")
                pygame.draw.rect(cell_surf, (border_color.r, border_color.g, border_color.b, alpha),
                               (0, 0, scaled, scaled), 2)
                render_surface.blit(cell_surf, (x + off, y + off))
            else:
                pygame.draw.rect(render_surface, "#d8dee9", (x, y, square_size, square_size), 2)

    # Draw tiles
    if not animating:
        # Static tiles: blit directly from cache (no threading needed)
        for r in range(rows):
            for c in range(cols):
                value = playingGrid[r][c]
                if value:
                    draw_tile(r, c, value)
    else:
        merging_positions = {(r, c) for r, c, _, _ in merging_tiles}

        # Draw static tiles from cache
        for r in range(rows):
            for c in range(cols):
                value = playingGrid[r][c]
                if value and (r, c) not in merging_positions and (r, c) != new_tile_pos:
                    is_moving_destination = any(er == r and ec == c for _, _, er, ec, _, _ in moving_tiles)
                    if not is_moving_destination or animation_progress >= 1.0:
                        draw_tile(r, c, value)

        # Draw moving tiles from cache
        for sr, sc, er, ec, val, progress in moving_tiles:
            r_pos = lerp(sr, er, progress)
            c_pos = lerp(sc, ec, progress)
            draw_tile(r_pos, c_pos, val)

        # Draw merging tiles
        for mr, mc, mval, mscale in merging_tiles:
            if mscale == 1.0:
                draw_tile(mr, mc, mval)
            else:
                surface = prepare_tile_surface(mval, mscale)
                if surface:
                    x = start_x + mc * square_size
                    y = start_y + mr * square_size
                    offset = (square_size - surface.get_width()) / 2
                    render_surface.blit(surface, (x + offset, y + offset))

        # Draw new tile spawn animation
        if new_tile_pos and new_tile_scale > 0:
            nr, nc = new_tile_pos
            nscale = ease_out_cubic(new_tile_scale)
            surface = prepare_tile_surface(playingGrid[nr][nc], nscale)
            if surface:
                x = start_x + nc * square_size
                y = start_y + nr * square_size
                offset = (square_size - surface.get_width()) / 2
                render_surface.blit(surface, (x + offset, y + offset))

    # Restore start positions after expansion animation drawing
    if grid_expanding:
        start_x, start_y = _expand_real_sx, _expand_real_sy

    if selecting_bomb_position:
        instruction_text = small_font.render("Click an empty tile to place bomb (ESC to cancel)", True, "#a3be8c")
        instruction_rect = instruction_text.get_rect(center=(RENDER_WIDTH//2, menu_y - 30))
        render_surface.blit(instruction_text, instruction_rect)
    else:
        menu_title = font.render("ABILITIES", True, "#eceff4")
        menu_title_rect = menu_title.get_rect(center=(RENDER_WIDTH//2, menu_y))
        render_surface.blit(menu_title, menu_title_rect)
    
    can_afford = points >= bomb_ability_cost
    draw_button(button_x, menu_y + 30, button_width, button_height, 
                "Bomb Tile", bomb_ability_cost, can_afford, selecting_bomb_position)
    
    # Render to OpenGL with CRT shader
    render_to_opengl()
    
    pygame.display.flip()

pygame.quit()
ctx.release()
