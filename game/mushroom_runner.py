#!/usr/bin/env python3
"""
MUSHROOM RUNNER - a side-scrolling platformer made with pygame.

Install:  pip install pygame
Run:      python mushroom_runner.py

Controls
  Left/Right or A/D ... move          Shift or X ... run
  Space/Up/W/Z ........ jump (hold = higher) - press again in the air = DOUBLE JUMP
  P ................... pause         F11 ... fullscreen / window      Esc ... quit

File layout (search for the "====" banners):
  1. CONFIG ....... every number / file path you might want to tweak
  2. LEVELS ....... level data (x3 longer) + level builder
  3. AUDIO ........ sound files, fallback beeps, background music
  4. IMAGES ....... image loading + scaling cache + sky
  5. PHYSICS ...... tile collision
  6. ENTITIES ..... Player, Walker (enemy), Mushroom
  7. GAME ......... setup, update, draw, main loop
"""
import array
import math
import os
import random
import sys

import pygame


# =====================================================================
# 1. CONFIG
# =====================================================================
# --- screen / tiles
TILE = 40
FPS = 60
SCREEN_W = 960 + 230
FRAME_TIME = 200  # milliseconds
# --- ground
GROUND_ROW = 12          # row where the ground surface is
GROUND_LAYERS = 10       # how many rows of ground (bricks) there are
ROWS = GROUND_ROW + GROUND_LAYERS
SCREEN_H = ROWS * TILE   # window height follows the number of rows
GROUND_Y = GROUND_ROW * TILE

SOLID_TILES = set("#BQMUG")   # tile characters you can't walk through

# --- player physics
WALK_SPEED = 230
RUN_SPEED = 340
GROUND_ACCEL = 1900
AIR_ACCEL = 1100
GROUND_FRICTION = 1700
AIR_FRICTION = 250
GRAVITY = 1900
SHORT_JUMP_GRAVITY_MULT = 2.3   # extra gravity when you release jump early
MAX_FALL_SPEED = 900
JUMP_SPEED = 720
RUN_JUMP_SPEED = 780            # used when moving faster than RUN_JUMP_THRESHOLD
RUN_JUMP_THRESHOLD = 250
MAX_AIR_JUMPS = 1               # 1 = double jump (set 2 for triple jump...)
COYOTE_TIME = 0.1               # grace time to jump after leaving a ledge
JUMP_BUFFER = 0.12              # remember jump press this long before landing
PLAYER_W, PLAYER_SMALL_H, PLAYER_BIG_H = 28, 38, 70
INVINCIBLE_TIME = 2.0

# --- level progression
LEVEL_REPEATS = 3               # every level is this many times longer than the base design
# Sky darkness per level: 0.0 = bright blue day ... 1.0 = pitch black night
DARKNESS = [0.0, 0.5, 1.0]
ENEMY_BONUS = [0, 4, 10]        # extra enemies added on top of the level design, per level

# --- fullscreen
START_FULLSCREEN = True         # start in fullscreen (F11 toggles it any time)

# --- audio files (relative paths are relative to this script)
MUSIC_VOLUME = 0.5
SFX_VOLUME = 0.8
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_FILE = "./sound/main.mp3"                # background song (loops)
JUMP = "./sound/jump.wav"                      # when jumping
DIE = "./sound/die.wav"                        # when dying: music stops, ONLY this plays
EAT = "./sound/eat_mushroom.wav"               # when eating a mushroom
COIN = "./sound/coin.wav"                      # when collecting a coin
WIN = "./sound/win.wav"                        # when finishing a level: music stops, ONLY this plays
LOSS_SCORE = "./sound/loss.wav"                # when big and hit -> becomes small
WALL = "./sound/wall.wav"                      # when a brick wall is broken
EXCLUSIVE_MAX_WAIT = 6.0                       # never wait longer than this for die/win sound to end

# --- image files
Mushroom_IMAGE = "./image/mushroom.png"
littile_man_frame1_IMAGE = "./image/little1.png"
littile_man_frame2_IMAGE = "./image/little2.png"
littile_man_frame3_IMAGE = "./image/little3.png"
big_main_frame1_IMAGE = "./image/big1.png"
big_main_frame2_IMAGE = "./image/big2.png"
big_main_frame3_IMAGE = "./image/big3.png"
coin_IMAGE = "./image/coin.png"      # spins like a real coin (change to your coin image)

# Every picture inside this folder is a monster skin.
# Each monster gets ONE random skin when the level starts (and keeps it).
MONSTER_DIR = "./monster"

LITTLE_FRAMES = [littile_man_frame1_IMAGE, littile_man_frame2_IMAGE, littile_man_frame3_IMAGE]
BIG_FRAMES = [big_main_frame1_IMAGE, big_main_frame2_IMAGE, big_main_frame3_IMAGE]

PLAYER_IMAGES_FACE_RIGHT = True     # False if your player pictures look to the LEFT
MONSTER_IMAGES_FACE_RIGHT = False   # False if your monster pictures look to the LEFT
FRAME_DIST = 1000                     
AIR_FRAME = 1                       # which frame (0,1,2) is shown while in the air
PLAYER_SPRITE_SCALE = 1.0           # make the player picture bigger/smaller than the hitbox
COIN_SIZE = 28

HI_FILE = os.path.join(BASE_DIR, "highscore.txt")


# =====================================================================
# 2. LEVELS
# =====================================================================
# Tile letters:  # ground/stairs   B brick   Q coin block   M mushroom block
#                U used block      G pipe
# blocks = (column, row, letter)     pipes = (column, height in tiles)
# gaps   = (start column, width)     coins = (column, row)
#
# Each entry below is ONE segment of length `period` columns. The game repeats it
# LEVEL_REPEATS times (the 2nd copy is mirrored so it does not feel identical),
# then adds the staircase, flag and castle at the end.
BASE_LEVELS = [
    dict(name="1-1", period=70, time=400, gaps=[(20, 3), (46, 3), (60, 2)],
         blocks=[(10, 8, "Q"), (11, 8, "B"), (12, 8, "M"), (13, 8, "B"), (14, 8, "Q"),
                 (28, 8, "B"), (29, 8, "Q"), (30, 8, "B"), (31, 8, "Q"), (32, 8, "B"), (30, 5, "Q"),
                 (52, 8, "M"), (53, 8, "B"), (54, 8, "Q"), (66, 8, "Q"), (67, 8, "B"), (68, 8, "Q")],
         enemies=[16, 25, 34, 38, 44, 56, 63, 64],
         coins=[(c, 6) for c in range(10, 15)] + [(c, 9) for c in (20, 21, 22, 46, 47, 48, 60, 61)],
         pipes=[(36, 2), (40, 3)]),
    dict(name="1-2", period=90, time=450, gaps=[(18, 3), (34, 4), (52, 3), (70, 3), (80, 2)],
         blocks=[(8, 8, "Q"), (9, 8, "M"), (10, 8, "Q"), (22, 8, "B"), (23, 8, "B"), (24, 8, "Q"),
                 (25, 8, "B"), (26, 8, "B"), (24, 5, "Q"), (40, 8, "Q"), (41, 8, "M"), (42, 8, "Q"),
                 (56, 8, "B"), (57, 8, "Q"), (58, 8, "B"), (74, 8, "Q"), (75, 8, "M")],
         enemies=[13, 28, 30, 44, 49, 61, 64, 66, 76, 85],
         coins=[(c, 6) for c in range(8, 11)] + [(c, 9) for c in (34, 35, 36, 37, 52, 53, 54, 70, 71, 72)] + [(24, 3)],
         pipes=[(14, 2), (46, 2), (62, 3)]),
    dict(name="1-3", period=108, time=500, gaps=[(15, 3), (30, 4), (44, 3), (60, 4), (78, 3), (92, 3), (102, 2)],
         blocks=[(8, 8, "M"), (9, 8, "Q"), (26, 8, "B"), (27, 8, "Q"), (28, 8, "B"), (27, 5, "M"),
                 (38, 8, "Q"), (39, 8, "B"), (40, 8, "Q"), (41, 8, "B"), (56, 8, "Q"), (57, 8, "M"),
                 (65, 8, "B"), (66, 8, "Q"), (67, 8, "B"), (82, 8, "Q"), (83, 8, "B"), (96, 8, "Q"), (97, 8, "M")],
         enemies=[12, 19, 25, 34, 36, 42, 48, 50, 57, 64, 68, 74, 76, 82, 90, 95, 99, 105],
         coins=[(c, 9) for c in (30, 31, 32, 33, 60, 61, 62, 63, 92, 93, 94)] + [(c, 6) for c in (38, 39, 40, 41)] + [(27, 3)],
         pipes=[(22, 3), (52, 2), (70, 3), (86, 2)]),
]


def expand_level(base, idx):
    """Repeat a base segment LEVEL_REPEATS times (odd copies are mirrored)."""
    P = base["period"]
    gaps, blocks, enemies, coins, pipes = [], [], [], [], []
    for k in range(LEVEL_REPEATS):
        o = k * P
        mir = k % 2 == 1
        for s, n in base["gaps"]:
            gaps.append((o + (P - s - n if mir else s), n))
        for c, r, ch in base["blocks"]:
            blocks.append((o + (P - 1 - c if mir else c), r, ch))
        for c in base["enemies"]:
            enemies.append(o + (P - 1 - c if mir else c))
        for c, r in base["coins"]:
            coins.append((o + (P - 1 - c if mir else c), r))
        for c, h in base["pipes"]:
            pipes.append((o + (P - c - 2 if mir else c), h))
    return dict(name=base["name"], width=P * LEVEL_REPEATS + 12, time=base["time"],
                gaps=gaps, blocks=blocks, enemies=enemies, coins=coins, pipes=pipes,
                extra_enemies=ENEMY_BONUS[min(idx, len(ENEMY_BONUS) - 1)], seed=idx)


LEVELS = [expand_level(b, i) for i, b in enumerate(BASE_LEVELS)]


def make_level(width, gaps, blocks, enemies, coins, pipes, time=250, name="1",
               extra_enemies=0, seed=0):
    """Turn the level description above into a 2D grid of tile letters."""
    grid = [[" "] * width for _ in range(ROWS)]

    # ground (GROUND_LAYERS rows deep), except in the gaps
    for col in range(width):
        if any(start <= col < start + n for start, n in gaps):
            continue
        for row in range(GROUND_ROW, ROWS):
            grid[row][col] = "#"

    # floating blocks
    for col, row, letter in blocks:
        if 0 <= col < width:
            grid[row][col] = letter

    # pipes (2 tiles wide)
    for col, height in pipes:
        for k in range(height):
            for cc in (col, col + 1):
                if 0 <= cc < width:
                    grid[GROUND_ROW - 1 - k][cc] = "G"

    # staircase before the flag
    base = width - 12
    for i in range(6):
        for k in range(i + 1):
            grid[GROUND_ROW - 1 - k][base + i] = "#"

    # extra enemies (more and more each level), placed on safe flat ground
    enemies = list(enemies)
    rnd = random.Random(seed * 7919 + 13)
    added = tries = 0
    while added < extra_enemies and tries < 4000:
        tries += 1
        col = rnd.randint(14, width - 18)
        if any(abs(col - e) < 4 for e in enemies):
            continue
        if all(grid[GROUND_ROW][c] == "#" and grid[GROUND_ROW - 1][c] == " "
               for c in (col - 1, col, col + 1)):
            enemies.append(col)
            added += 1

    return dict(grid=grid, width=width, enemies=enemies, coins=list(coins),
                flag=width - 4, time=time, name=name)


# =====================================================================
# 3. AUDIO
# =====================================================================
SFX = {}
_excl = {"locked": False, "chan": None}


def asset_path(p):
    if not p:
        return None
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(BASE_DIR, p))


def tone_bytes(f0, f1, ms, vol=0.25, wave="sq"):
    """Raw 16-bit mono samples of a sweeping tone (f0 -> f1 Hz)."""
    n = int(22050 * ms / 1000)
    samples = array.array("h")
    for i in range(n):
        t = i / n
        phase = (i * (f0 + (f1 - f0) * t) / 22050) % 1
        v = (1 if phase < 0.5 else -1) if wave == "sq" else math.sin(phase * 6.2832)
        samples.append(int(v * vol * 32767 * (1 - t)))
    return samples.tobytes()


def tone(f0, f1, ms, vol=0.25, wave="sq"):
    return pygame.mixer.Sound(buffer=tone_bytes(f0, f1, ms, vol, wave))


def load_sound(path):
    fp = asset_path(path)
    if not fp or not os.path.isfile(fp):
        print("Sound file not found (using built-in beep):", path)
        return None
    try:
        return pygame.mixer.Sound(fp)
    except Exception as ex:
        print("Could not load sound", path, "->", ex)
        return None


def init_sound():
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(22050, -16, 1, 512)
        except Exception:
            return
    pygame.mixer.set_num_channels(16)

    # built-in beeps = fallback if a file is missing
    synth = dict(jump=lambda: tone(300, 650, 140), coin=lambda: tone(900, 1400, 120),
                 stomp=lambda: tone(250, 90, 120), eat=lambda: tone(300, 1100, 380),
                 loss=lambda: tone(500, 120, 300), bump=lambda: tone(130, 90, 90),
                 brick=lambda: tone(200, 60, 160, wave="sin"), win=lambda: tone(500, 1300, 700),
                 die=lambda: tone(600, 100, 800))
    for name, make in synth.items():
        try:
            SFX[name] = make()
        except Exception:
            pass

    # "brick" = the sound of breaking a wall (WALL file)
    files = dict(jump=JUMP, die=DIE, eat=EAT, coin=COIN, win=WIN, loss=LOSS_SCORE, brick=WALL)
    for name, path in files.items():
        s = load_sound(path)
        if s is not None:
            SFX[name] = s

    for s in SFX.values():
        s.set_volume(SFX_VOLUME)


def play(name):
    """Normal sound effect (ignored while a die/win sound owns the speakers)."""
    if _excl["locked"]:
        return
    s = SFX.get(name)
    if s:
        s.play()


def play_exclusive(name):
    """Stop the music and every other sound, play ONLY this one.
    Everything else stays muted until unlock_audio() is called."""
    MUSIC.stop()
    if pygame.mixer.get_init():
        pygame.mixer.stop()
    _excl["locked"] = True
    s = SFX.get(name)
    _excl["chan"] = s.play() if s else None


def unlock_audio():
    _excl["locked"] = False
    _excl["chan"] = None


def exclusive_busy():
    ch = _excl["chan"]
    return bool(ch and ch.get_busy())


class Music:
    """Background music: loops YOUR song file (see MUSIC_FILE in CONFIG)."""

    def __init__(self):
        self.playing = False

    def start(self):
        self.stop()
        if _excl["locked"] or not pygame.mixer.get_init():
            return
        fp = asset_path(MUSIC_FILE)
        if not fp or not os.path.isfile(fp):
            print("Music file not found:", MUSIC_FILE)
            return
        try:
            pygame.mixer.music.load(fp)
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play(-1)      # -1 = loop forever
            self.playing = True
        except Exception as ex:
            print("Could not play music file:", ex)

    def stop(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.playing = False

    def pause(self):
        if self.playing:
            pygame.mixer.music.pause()

    def resume(self):
        if self.playing:
            pygame.mixer.music.unpause()


MUSIC = Music()


# =====================================================================
# 4. IMAGES
# =====================================================================
_scaled_cache = {}


def load_image(path):
    fp = asset_path(path)
    if not fp or not os.path.isfile(fp):
        print("Image not found (using drawn version):", path)
        return None
    try:
        return pygame.image.load(fp).convert_alpha()
    except Exception as ex:
        print("Could not load image", path, "->", ex)
        return None


def load_frames(paths):
    return [img for img in (load_image(p) for p in paths) if img is not None]


def load_folder(path):
    """Load every picture (png/jpg/webp) inside a folder."""
    fp = asset_path(path)
    if not fp or not os.path.isdir(fp):
        print("Image folder not found (using drawn monsters):", path)
        return []
    names = sorted(f for f in os.listdir(fp)
                   if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))
    return [img for img in (load_image(os.path.join(fp, n)) for n in names) if img is not None]


def scaled(img, w, h, flip=False):
    """Smooth-scaled (and optionally mirrored) copy, cached."""
    w, h = max(1, int(w)), max(1, int(h))
    key = (id(img), w, h, flip)
    s = _scaled_cache.get(key)
    if s is None:
        s = pygame.transform.smoothscale(img, (w, h))
        if flip:
            s = pygame.transform.flip(s, True, False)
        _scaled_cache[key] = s
    return s


def sprite_w(img, h):
    return max(1, round(img.get_width() * h / img.get_height()))


def scaled_h(img, h, flip=False):
    """Scale to a wanted height, keeping the picture's proportions."""
    return scaled(img, sprite_w(img, h), h, flip)


def make_sky(dark):
    """Sky gradient. dark = 0.0 (bright blue) ... 1.0 (black). Only the sky changes."""
    sky = pygame.Surface((SCREEN_W, SCREEN_H))
    m = 1.0 - max(0.0, min(1.0, dark))
    for y in range(SCREEN_H):
        k = y / SCREEN_H
        col = (int((90 + 120 * k) * m), int((160 + 70 * k) * m), int(245 * m))
        pygame.draw.line(sky, col, (0, y), (SCREEN_W, y))
    return sky


# =====================================================================
# 5. PHYSICS
# =====================================================================
def tiles_hit(level, e):
    """All solid tiles (col, row) that entity `e` overlaps."""
    out = []
    r = pygame.Rect(int(e.x), int(e.y), e.w, e.h)
    for col in range(r.left // TILE, (r.right - 1) // TILE + 1):
        for row in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
            if col < 0 or col >= level["width"]:
                out.append((col, row))
            elif 0 <= row < ROWS and level["grid"][row][col] in SOLID_TILES:
                out.append((col, row))
    return out


def move(level, e, dt, on_bump=None):
    """Axis-separated tile collision. Sets e.on; returns True if a wall was hit.
    on_bump(col, row) is called when the entity hits a tile with its head."""
    e.on, hit_wall = False, False

    # horizontal
    e.x += e.vx * dt
    hit = tiles_hit(level, e)
    if hit:
        col = hit[0][0]
        e.x = col * TILE - e.w if e.vx > 0 else (col + 1) * TILE
        hit_wall = True

    # vertical
    e.y += e.vy * dt
    hit = tiles_hit(level, e)
    if hit:
        if e.vy > 0:                                   # landing
            e.y = hit[0][1] * TILE - e.h
            e.on = True
        elif e.vy < 0:                                 # head bump
            cx = e.x + e.w / 2
            col, row = min(hit, key=lambda t: abs(t[0] * TILE + TILE / 2 - cx))
            e.y = (max(t[1] for t in hit) + 1) * TILE
            if on_bump:
                on_bump(col, row)
        e.vy = 0
    return hit_wall


# =====================================================================
# 6. ENTITIES
# =====================================================================
class Player:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.anim_timer = 0.0
        self.walk_frame = 1
        self.vx = self.vy = 0.0
        self.w, self.h = PLAYER_W, PLAYER_SMALL_H
        self.big = False
        self.on = False                 # standing on ground
        self.face = 1                   # 1 = right, -1 = left
        self.inv = 0.0                  # invincibility timer
        self.coyote = 0.0
        self.buf = 0.0                  # jump buffer timer
        self.air_jumps = MAX_AIR_JUMPS  # extra jumps left while in the air
        self.anim = 0.0                 # distance walked (drives the walk frames)
        self.dead = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def set_big(self):
        self.y -= PLAYER_BIG_H - PLAYER_SMALL_H
        self.big, self.h = True, PLAYER_BIG_H

    def set_small(self):
        self.y += PLAYER_BIG_H - PLAYER_SMALL_H
        self.big, self.h = False, PLAYER_SMALL_H


class Walker:
    """The mushroom-monster enemy. Each one has ONE fixed random skin."""

    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, 32, 32
        self.vx, self.vy = -60.0, 0.0
        self.alive, self.t, self.on = True, 0.5, False   # t = squashed-corpse timer
        self.skin = 0                                    # index of the picture in the monster folder


class Mushroom:
    """Power-up item."""

    def __init__(self, x, y):
        self.x, self.y, self.w, self.h = x, y, 32, 32
        self.vx, self.vy = 90.0, 0.0
        self.on, self.alive = False, True


# =====================================================================
# 7. GAME
# =====================================================================
class Game:
    # ---------------------------------------------------------- setup
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        init_sound()
        flags = pygame.SCALED | (pygame.FULLSCREEN if START_FULLSCREEN else 0)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
        pygame.display.set_caption("Mushroom Runner")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.font_med = pygame.font.SysFont("arial", 34, bold=True)
        self.font_big = pygame.font.SysFont("arial", 76, bold=True)
        self.font_small = pygame.font.SysFont("arial", 16, bold=True)
        self.qmark = self.font_med.render("?", True, (120, 70, 0))

        self.load_assets()

        self.state = "title"     # title / play / pause / dying / clear / gameover / win
        self.t = 0.0
        self.hi = self.load_hi()
        self.particles, self.popups, self.score = [], [], 0
        self.banner = 0.0
        self.lvl = 0

        self._make_background()

    def load_assets(self):
        self.img_mushroom = load_image(Mushroom_IMAGE)
        self.img_coin = load_image(coin_IMAGE)
        self.small_frames = load_frames(LITTLE_FRAMES)
        self.big_frames = load_frames(BIG_FRAMES)
        self.monster_frames = load_folder(MONSTER_DIR)

    def _make_background(self):
        rnd = random.Random(4)
        self.clouds = [(rnd.randint(0, 1400), rnd.randint(30, 190), rnd.uniform(0.7, 1.3)) for _ in range(9)]
        self.hills = [(rnd.randint(0, 1400), rnd.randint(120, 220)) for _ in range(6)]
        self.sky_day = make_sky(0.0)      # used on the title screen
        self.sky = self.sky_day           # replaced by a darker sky in later levels

    def load_hi(self):
        try:
            with open(HI_FILE) as f:
                return int(f.read())
        except Exception:
            return 0

    def save_hi(self):
        self.hi = max(self.hi, self.score)
        try:
            with open(HI_FILE, "w") as f:
                f.write(str(self.hi))
        except Exception:
            pass

    def new_game(self):
        self.score, self.coins, self.lives, self.lvl = 0, 0, 3, 0
        self.start_level()

    def start_level(self, keep_big=False):
        self.level = make_level(**LEVELS[self.lvl])
        self.player = Player(2 * TILE, GROUND_Y - PLAYER_SMALL_H)
        if keep_big:
            self.player.set_big()
        self.enemies = [Walker(c * TILE + 4, GROUND_Y - 32) for c in self.level["enemies"]]
        # every monster gets ONE random picture (and keeps it)
        for e in self.enemies:
            e.skin = random.randrange(len(self.monster_frames)) if self.monster_frames else 0
        self.coin_list = [[c * TILE + TILE // 2, r * TILE + TILE // 2] for c, r in self.level["coins"]]
        self.items, self.particles, self.popups = [], [], []
        self.time, self.time_acc = self.level["time"], 0.0
        self.cam = 0.0
        self.banner = 2.2
        self.state = "play"

        # only the SKY gets darker every level (blue -> dark blue -> black)
        self.sky = make_sky(DARKNESS[min(self.lvl, len(DARKNESS) - 1)])

        # music (die / win sounds have finished by now)
        unlock_audio()
        if not MUSIC.playing:
            MUSIC.start()

    # -------------------------------------------------------- helpers
    def popup(self, x, y, text):
        self.popups.append([x, y, text, 1.0])

    def burst(self, x, y, color, n=8):
        for _ in range(n):
            self.particles.append([x, y, random.uniform(-160, 160), random.uniform(-380, -80), 0.8, color])

    def jump_held(self):
        k = pygame.key.get_pressed()
        return k[pygame.K_SPACE] or k[pygame.K_UP] or k[pygame.K_w] or k[pygame.K_z]

    def die(self):
        if self.player.dead or self.state != "play":
            return
        p = self.player
        p.dead, p.vy, p.vx = True, -650.0, 0.0
        self.state, self.timer = "dying", 2.0
        play_exclusive("die")            # music off, only the death sound

    def hurt(self):
        p = self.player
        if p.inv > 0:
            return
        if p.big:
            p.set_small()
            p.inv = INVINCIBLE_TIME
            play("loss")
        else:
            self.die()

    def hit_block(self, col, row):
        """Called when the player's head bumps tile (col, row)."""
        grid = self.level["grid"]
        ch = grid[row][col]
        if ch == "Q":                                   # coin block
            grid[row][col] = "U"
            self.coins += 1
            self.score += 200
            self.popup(col * TILE, row * TILE - 10, "+200")
            self.burst(col * TILE + 20, row * TILE, (255, 215, 0), 5)
            play("coin")
        elif ch == "M":                                 # mushroom block
            grid[row][col] = "U"
            self.items.append(Mushroom(col * TILE + 4, row * TILE - 32))
            play("bump")
        elif ch == "B":                                 # brick wall breaks
            grid[row][col] = " "
            self.score += 50
            self.burst(col * TILE + 20, row * TILE + 20, (190, 100, 50), 10)
            play("brick")                               # wall-breaking sound
        else:
            play("bump")

    # ------------------------------------------------------- updates
    def update_play(self, dt):
        self._update_timer(dt)
        if self.state != "play":
            return
        self._update_player(dt)
        if self.state != "play":
            return
        self._collect_coins()
        self._update_items(dt)
        self._update_enemies(dt)
        self._check_goal()

    def _update_timer(self, dt):
        self.time_acc += dt
        if self.time_acc >= 1:
            self.time_acc -= 1
            self.time -= 1
            if self.time <= 0:
                self.die()

    def _update_player(self, dt):
        p, level = self.player, self.level
        k = pygame.key.get_pressed()
        direction = (k[pygame.K_RIGHT] or k[pygame.K_d]) - (k[pygame.K_LEFT] or k[pygame.K_a])
        running = k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT] or k[pygame.K_x]
        held = self.jump_held()

        # --- horizontal movement
        vmax = RUN_SPEED if running else WALK_SPEED
        accel = GROUND_ACCEL if p.on else AIR_ACCEL
        if direction:
            if direction * p.vx < 0:        # turning around is faster
                accel *= 2
            p.vx = max(-vmax, min(vmax, p.vx + direction * accel * dt))
            p.face = direction
        else:
            friction = (GROUND_FRICTION if p.on else AIR_FRICTION) * dt
            p.vx = 0 if abs(p.vx) <= friction else p.vx - math.copysign(friction, p.vx)

        # --- jumping (ground jump + air jumps)
        if p.on:
            p.air_jumps = MAX_AIR_JUMPS
        if p.buf > 0:
            if p.on or p.coyote > 0:            # normal jump
                self._do_jump(p)
            elif p.air_jumps > 0:               # double jump
                p.air_jumps -= 1
                self._do_jump(p)

        # --- gravity + collision
        gravity = GRAVITY * (SHORT_JUMP_GRAVITY_MULT if (p.vy < 0 and not held) else 1)
        p.vy = min(MAX_FALL_SPEED, p.vy + gravity * dt)
        move(level, p, dt, self.hit_block)

        p.coyote = COYOTE_TIME if p.on else max(0, p.coyote - dt)
        p.buf = max(0, p.buf - dt)
        p.inv = max(0, p.inv - dt)
        p.anim += abs(p.vx) * dt

        if p.on and abs(p.vx) > 8:
            p.anim_timer += dt
            frame_time = FRAME_TIME / 1000.0

            frames = self.big_frames if p.big else self.small_frames

            while p.anim_timer >= frame_time:
                p.anim_timer -= frame_time

                if len(frames) > 1:
                    p.walk_frame += 1

                    if p.walk_frame >= len(frames):
                        p.walk_frame = 1
        else:
            p.anim_timer = 0.0
            p.walk_frame = 1
        # --- camera (never scrolls back) and screen limits
        if p.x < self.cam:
            p.x, p.vx = self.cam, 0
        self.cam = max(self.cam, min(p.x - SCREEN_W * 0.4, level["width"] * TILE - SCREEN_W))
        if p.y > SCREEN_H + 60:
            self.die()

    def _do_jump(self, p):
        p.vy = -RUN_JUMP_SPEED if abs(p.vx) > RUN_JUMP_THRESHOLD else -JUMP_SPEED
        p.buf = p.coyote = 0
        p.on = False
        play("jump")

    def _collect_coins(self):
        p = self.player
        pr = p.rect
        for c in self.coin_list[:]:
            if abs(pr.centerx - c[0]) < 26 and abs(pr.centery - c[1]) < p.h / 2 + 14:
                self.coin_list.remove(c)
                self.coins += 1
                self.score += 100
                play("coin")

    def _update_items(self, dt):
        p, level = self.player, self.level
        pr = p.rect
        for it in self.items:
            it.vy = min(MAX_FALL_SPEED, it.vy + GRAVITY * dt)
            if move(level, it, dt):
                it.vx = -it.vx
            if it.y > SCREEN_H + 60:
                it.alive = False
            elif pr.colliderect(pygame.Rect(int(it.x), int(it.y), it.w, it.h)):
                it.alive = False
                self.score += 1000
                self.popup(it.x, it.y, "+1000")
                play("eat")
                if not p.big and self._room_to_grow():
                    p.set_big()
        self.items = [i for i in self.items if i.alive]

    def _room_to_grow(self):
        """True if there is no solid tile in the space the big player needs."""
        p, grid = self.player, self.level["grid"]
        cols = range(int(p.x) // TILE, (int(p.x) + p.w - 1) // TILE + 1)
        rows = range(int(p.y - 32) // TILE, int(p.y) // TILE)
        return not any(c < 0 or r < 0 or grid[r][c] in SOLID_TILES for c in cols for r in rows)

    def _update_enemies(self, dt):
        p, level = self.player, self.level
        pr = p.rect
        for e in self.enemies:
            if not e.alive:
                e.t -= dt
                continue
            if abs(e.x - (self.cam + SCREEN_W / 2)) > SCREEN_W * 0.75:   # off-screen: sleep
                continue
            e.vy = min(MAX_FALL_SPEED, e.vy + GRAVITY * dt)
            if move(level, e, dt):
                e.vx = -e.vx
            if e.y > SCREEN_H + 60:
                e.alive, e.t = False, 0
                continue
            er = pygame.Rect(int(e.x), int(e.y), e.w, e.h)
            if pr.colliderect(er) and not p.dead:
                if p.vy > 0 and (p.y + p.h) - e.y < 26:     # stomped
                    e.alive = False
                    p.vy = -640 if self.jump_held() else -420
                    self.score += 100
                    self.popup(e.x, e.y - 10, "+100")
                    self.burst(e.x + 16, e.y + 16, (150, 90, 40), 6)
                    play("stomp")
                else:
                    self.hurt()
        self.enemies = [e for e in self.enemies if e.alive or e.t > 0]

    def _check_goal(self):
        p, level = self.player, self.level
        if p.x + p.w > level["flag"] * TILE + 14 and not p.dead:
            self.state, self.phase, self.bonus_acc, self.wait = "clear", 0, 0.0, 0.8
            p.vx = p.vy = 0
            p.on = False
            p.x = level["flag"] * TILE - p.w + 18
            self.score += max(100, int((GROUND_Y - p.y) / 8) * 100)
            play_exclusive("win")        # music off, only the win sound

    def update_clear(self, dt):
        """Level-clear sequence: slide down -> walk to castle -> time bonus -> next level."""
        p = self.player
        if self.phase == 0:
            p.y = min(p.y + 220 * dt, GROUND_Y - p.h)
            if p.y >= GROUND_Y - p.h:
                self.phase = 1
        elif self.phase == 1:
            p.on, p.vx = True, 130
            p.x += 130 * dt
            p.face, p.anim = 1, p.anim + 130 * dt
            if p.x > (self.level["flag"] + 1.5) * TILE:
                self.phase = 2
        elif self.phase == 2:
            self.bonus_acc += dt * 120
            while self.bonus_acc >= 1 and self.time > 0:
                self.bonus_acc -= 1
                self.time -= 1
                self.score += 50
            if self.time <= 0:
                self.phase = 3
        else:
            self.wait -= dt
            # wait until the win sound has finished (but never forever)
            if self.wait <= 0 and (not exclusive_busy() or self.wait < -EXCLUSIVE_MAX_WAIT):
                self.lvl += 1
                if self.lvl >= len(LEVELS):
                    self.lvl = len(LEVELS) - 1
                    self.save_hi()
                    MUSIC.stop()
                    self.state = "win"
                else:
                    self.start_level(keep_big=p.big)

    def update_dying(self, dt):
        p = self.player
        p.vy += 1500 * dt
        p.y += p.vy * dt
        self.timer -= dt
        # wait until the death sound has finished (but never forever)
        if self.timer <= 0 and (not exclusive_busy() or self.timer < -EXCLUSIVE_MAX_WAIT):
            self.lives -= 1
            if self.lives <= 0:
                self.save_hi()
                MUSIC.stop()
                self.state = "gameover"
            else:
                self.start_level()

    def update(self, dt):
        self.t += dt
        self.banner = max(0.0, self.banner - dt)
        if self.state == "play":
            self.update_play(dt)
        elif self.state == "clear":
            self.update_clear(dt)
        elif self.state == "dying":
            self.update_dying(dt)

        for q in self.particles:
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[3] += 1200 * dt
            q[4] -= dt
        self.particles = [q for q in self.particles if q[4] > 0]
        for q in self.popups:
            q[1] -= 40 * dt
            q[3] -= dt
        self.popups = [q for q in self.popups if q[3] > 0]

    # -------------------------------------------------------- drawing
    def text(self, txt, x, y, font=None, col=(255, 255, 255), center=False):
        font = font or self.font
        img = font.render(txt, True, col)
        shadow = font.render(txt, True, (20, 20, 40))
        r = img.get_rect(center=(x, y)) if center else img.get_rect(topleft=(x, y))
        self.screen.blit(shadow, r.move(2, 2))
        self.screen.blit(img, r)

    def draw_world(self):
        cam = int(self.cam)
        self.screen.blit(self.sky, (0, 0))
        self._draw_background(cam)
        self._draw_tiles(cam)
        self._draw_flag_and_castle(cam)
        self._draw_coins(cam)
        self._draw_items(cam)
        self._draw_enemies(cam)

        p = self.player
        blink = p.inv > 0 and int(self.t * 20) % 2
        hidden = self.state == "clear" and self.phase >= 2
        if not blink and not hidden:
            self.draw_player(p, cam)

        for q in self.particles:
            pygame.draw.rect(self.screen, q[5], (q[0] - cam, q[1], 7, 7))
        for q in self.popups:
            self.text(q[2], q[0] - cam, q[1], self.font_small)

    def _draw_background(self, cam):
        scr = self.screen
        for hx, hh in self.hills:
            px = (hx - cam * 0.5) % (SCREEN_W + 500) - 250
            pygame.draw.ellipse(scr, (96, 190, 100), (px - 170, GROUND_Y - hh, 340, hh * 2))
        for cx, cy, sc in self.clouds:
            px = (cx - cam * 0.25) % (SCREEN_W + 300) - 150
            for dx, dy, r in ((0, 0, 26), (26, -8, 32), (58, 0, 26), (28, 8, 24)):
                pygame.draw.circle(scr, (255, 255, 255), (int(px + dx * sc), int(cy + dy * sc)), int(r * sc))

    def _draw_tiles(self, cam):
        grid, width = self.level["grid"], self.level["width"]
        for c in range(cam // TILE, min(width, cam // TILE + SCREEN_W // TILE + 2)):
            for r in range(ROWS):
                ch = grid[r][c]
                if ch != " ":
                    self._draw_tile(ch, pygame.Rect(c * TILE - cam, r * TILE, TILE, TILE), grid, c, r)

    def _draw_tile(self, ch, rc, grid, c, r):
        scr = self.screen
        if ch == "#":                                       # ground
            pygame.draw.rect(scr, (150, 95, 45), rc)
            pygame.draw.rect(scr, (110, 65, 30), rc, 2)
            if r == 0 or grid[r - 1][c] not in SOLID_TILES:   # grass on top
                pygame.draw.rect(scr, (80, 190, 70), (rc.x, rc.y, TILE, 10))
                pygame.draw.rect(scr, (50, 140, 50), (rc.x, rc.y + 10, TILE, 3))
        elif ch == "B":                                     # brick
            line = (110, 50, 25)
            pygame.draw.rect(scr, (200, 100, 50), rc)
            for yy in (13, 26):
                pygame.draw.line(scr, line, (rc.x, rc.y + yy), (rc.right, rc.y + yy), 2)
            pygame.draw.line(scr, line, (rc.x + 20, rc.y), (rc.x + 20, rc.y + 13), 2)
            pygame.draw.line(scr, line, (rc.x + 10, rc.y + 13), (rc.x + 10, rc.y + 26), 2)
            pygame.draw.line(scr, line, (rc.x + 30, rc.y + 13), (rc.x + 30, rc.y + 26), 2)
            pygame.draw.rect(scr, line, rc, 2)
        elif ch in "QM":                                    # ? block
            glow = int(30 * (math.sin(self.t * 6) + 1) / 2)
            pygame.draw.rect(scr, (235, 170 + glow, 30), rc)
            pygame.draw.rect(scr, (140, 90, 10), rc, 3)
            scr.blit(self.qmark, self.qmark.get_rect(center=rc.center))
        elif ch == "U":                                     # used block
            pygame.draw.rect(scr, (120, 90, 60), rc)
            pygame.draw.rect(scr, (80, 55, 35), rc, 3)
        elif ch == "G":                                     # pipe
            pygame.draw.rect(scr, (40, 170, 70), rc)
            left = c == 0 or grid[r][c - 1] != "G"
            pygame.draw.rect(scr, (120, 230, 130), (rc.x + (6 if left else 0), rc.y, 8, TILE))
            pygame.draw.rect(scr, (20, 100, 40), (rc.x if left else rc.right - 3, rc.y, 3, TILE))
            if r == 0 or grid[r - 1][c] != "G":             # pipe rim
                pygame.draw.rect(scr, (30, 150, 60), (rc.x - (4 if left else 0), rc.y, TILE + 4, 16))
                pygame.draw.rect(scr, (15, 90, 35), (rc.x - (4 if left else 0), rc.y, TILE + 4, 16), 2)

    def _draw_flag_and_castle(self, cam):
        scr, level = self.screen, self.level
        fx = level["flag"] * TILE - cam + TILE // 2
        top = GROUND_Y - 8 * TILE
        pygame.draw.rect(scr, (230, 230, 230), (fx - 3, top, 6, 8 * TILE))
        pygame.draw.circle(scr, (255, 215, 0), (fx, top), 9)
        pygame.draw.polygon(scr, (60, 200, 90), [(fx - 4, top + 8), (fx - 44, top + 24), (fx - 4, top + 40)])

        cx0 = (level["width"] - 3) * TILE - cam
        pygame.draw.rect(scr, (170, 90, 60), (cx0, GROUND_Y - 80, 3 * TILE, 80))
        for i in range(3):
            pygame.draw.rect(scr, (170, 90, 60), (cx0 + i * 44, GROUND_Y - 100, 28, 20))
        pygame.draw.rect(scr, (40, 20, 20), (cx0 + 44, GROUND_Y - 44, 32, 44),
                         border_top_left_radius=16, border_top_right_radius=16)

    def _draw_coins(self, cam):
        """Spinning coins: the picture gets thin and wide again, like a real turning coin."""
        for c in self.coin_list:
            sx = c[0] - cam
            if sx < -40 or sx > SCREEN_W + 40:
                continue
            k = abs(math.cos(self.t * 5 + c[0] * 0.01))
            if self.img_coin is not None:
                w = max(3, int(COIN_SIZE * k))
                spr = scaled(self.img_coin, w, COIN_SIZE)
                self.screen.blit(spr, (int(sx - w / 2), int(c[1] - COIN_SIZE / 2)))
            else:
                w = int(k * 14) + 3
                pygame.draw.ellipse(self.screen, (255, 205, 30), (sx - w // 2, c[1] - 12, w, 24))
                pygame.draw.ellipse(self.screen, (190, 140, 10), (sx - w // 2, c[1] - 12, w, 24), 2)

    def _draw_items(self, cam):
        scr = self.screen
        for it in self.items:
            x, y = it.x - cam, it.y
            if self.img_mushroom is not None:
                spr = scaled_h(self.img_mushroom, it.h)
                scr.blit(spr, (int(x + (it.w - spr.get_width()) / 2), int(y)))
                continue
            pygame.draw.rect(scr, (250, 235, 200), (x + 8, y + 16, 16, 16), border_radius=4)
            pygame.draw.ellipse(scr, (220, 40, 40), (x, y, 32, 24))
            pygame.draw.circle(scr, (255, 255, 255), (int(x + 9), int(y + 10)), 4)
            pygame.draw.circle(scr, (255, 255, 255), (int(x + 22), int(y + 8)), 4)

    def _draw_enemies(self, cam):
        scr = self.screen
        frames = self.monster_frames
        for e in self.enemies:
            x, y = e.x - cam, e.y
            if x < -80 or x > SCREEN_W + 80:
                continue

            # ----- with pictures: each monster always uses its own random skin
            if frames:
                img = frames[e.skin % len(frames)]
                flip = (e.vx < 0) if MONSTER_IMAGES_FACE_RIGHT else (e.vx > 0)
                if not e.alive:                             # squashed
                    w = sprite_w(img, e.h)
                    scr.blit(scaled(img, w, 10, flip), (int(x + (e.w - w) / 2), int(y + e.h - 10)))
                    continue
                spr = scaled_h(img, e.h, flip)
                scr.blit(spr, (int(x + (e.w - spr.get_width()) / 2), int(y)))
                continue

            # ----- drawn version (no pictures found)
            if not e.alive:
                pygame.draw.ellipse(scr, (140, 80, 40), (x, y + 22, 32, 10))
                continue
            sw = 3 if int(self.t * 6) % 2 else -3
            pygame.draw.rect(scr, (60, 35, 20), (x + 2 + sw, y + 24, 12, 8), border_radius=3)
            pygame.draw.rect(scr, (60, 35, 20), (x + 18 - sw, y + 24, 12, 8), border_radius=3)
            pygame.draw.ellipse(scr, (150, 85, 40), (x, y, 32, 28))
            for ex in (9, 23):
                pygame.draw.circle(scr, (255, 255, 255), (int(x + ex), int(y + 12)), 5)
                pygame.draw.circle(scr, (0, 0, 0), (int(x + ex + (1 if e.vx > 0 else -1)), int(y + 13)), 2)
            pygame.draw.line(scr, (50, 20, 10), (x + 3, y + 5), (x + 13, y + 9), 3)
            pygame.draw.line(scr, (50, 20, 10), (x + 29, y + 5), (x + 19, y + 9), 3)

    def draw_player(self, p, cam):
        frames = self.big_frames if p.big else self.small_frames
        if not frames:
            self.draw_player_vector(p, cam)
            return

        # frame choice: standing = 1st, walking = 1 -> 2 -> 3 -> 1 ..., in the air = AIR_FRAME
        if not p.on:
            idx = min(AIR_FRAME, len(frames) - 1)

        elif abs(p.vx) > 8:
            idx = min(p.walk_frame, len(frames) - 1)

        else:
            idx = 0

        flip = (p.face < 0) if PLAYER_IMAGES_FACE_RIGHT else (p.face > 0)
        sh = int(p.h * PLAYER_SPRITE_SCALE)
        spr = scaled_h(frames[idx], sh, flip)
        x = p.x - cam + p.w / 2 - spr.get_width() / 2
        y = p.y + p.h - sh
        self.screen.blit(spr, (int(x), int(y)))

    def draw_player_vector(self, p, cam):
        scr, x, y, f = self.screen, p.x - cam, p.y, p.face
        head_h = int(p.h * 0.3)
        swing = int(math.sin(p.anim * 0.09) * 5) if p.on else 6
        body_y = y + 10 + head_h
        pygame.draw.rect(scr, (60, 40, 30), (x + 3 + swing, y + p.h - 9, 11, 9), border_radius=3)
        pygame.draw.rect(scr, (60, 40, 30), (x + 14 - swing, y + p.h - 9, 11, 9), border_radius=3)
        pygame.draw.rect(scr, (40, 90, 220), (x + 2, body_y, 24, p.h - 10 - head_h - 6), border_radius=4)
        pygame.draw.rect(scr, (250, 210, 40), (x + 7, body_y + 6, 5, 5))
        pygame.draw.rect(scr, (250, 210, 40), (x + 16, body_y + 6, 5, 5))
        pygame.draw.rect(scr, (245, 195, 150), (x + 2, y + 8, 24, head_h + 2), border_radius=5)
        pygame.draw.circle(scr, (30, 30, 30), (int(x + (19 if f > 0 else 9)), int(y + 8 + head_h * 0.4)), 2)
        pygame.draw.rect(scr, (210, 40, 40), (x, y, 28, 11), border_top_left_radius=9, border_top_right_radius=9)
        pygame.draw.rect(scr, (210, 40, 40), (x + (12 if f > 0 else -2), y + 7, 18, 5), border_radius=2)

    def draw_hud(self):
        self.text("SCORE %06d" % self.score, 20, 12)
        self.text("COINS x%02d" % self.coins, 230, 12)
        self.text("WORLD %s" % self.level["name"], 400, 12)
        self.text("TIME %03d" % max(0, self.time), 560, 12)
        self.text("LIVES x%d" % self.lives, 720, 12)
        self.text("HI %06d" % self.hi, 850, 12, self.font_small)

    def draw_overlay(self, title, sub, col=(255, 240, 120)):
        veil = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 140))
        self.screen.blit(veil, (0, 0))
        self.text(title, SCREEN_W // 2, SCREEN_H // 2 - 50, self.font_big, col, True)
        self.text(sub, SCREEN_W // 2, SCREEN_H // 2 + 30, self.font_med, (255, 255, 255), True)

    def draw_title(self):
        scr = self.screen
        scr.blit(self.sky_day, (0, 0))
        for i in range(30):
            pygame.draw.rect(scr, (80, 190, 70), (i * TILE, GROUND_Y, TILE, 10))
            pygame.draw.rect(scr, (150, 95, 45), (i * TILE, GROUND_Y + 10, TILE, SCREEN_H))
        cx = SCREEN_W // 2
        self.text("MUSHROOM RUNNER", cx, 150, self.font_big, (255, 240, 120), True)
        self.text("A pygame platformer", cx, 215, self.font_med, (255, 255, 255), True)
        if int(self.t * 2) % 2 == 0:
            self.text("Press ENTER to start", cx, 300, self.font_med, (255, 255, 255), True)
        help_lines = ("Arrows / A D: move    Shift / X: run    Space / Up / W: jump (twice = double jump)",
                      "Stomp enemies, hit ? blocks, eat mushrooms, reach the flag",
                      "3 worlds - every world is longer, darker and has more enemies",
                      "P: pause    F11: fullscreen    Esc: quit")
        for i, line in enumerate(help_lines):
            self.text(line, cx, 380 + i * 30, self.font, (255, 255, 255), True)
        self.text("HI %06d" % self.hi, cx, 520, self.font, (255, 215, 0), True)

    def draw(self):
        if self.state == "title":
            self.draw_title()
            return
        self.draw_world()
        self.draw_hud()
        if self.state == "play" and self.banner > 0:
            self.text("WORLD %s" % self.level["name"], SCREEN_W // 2, 150, self.font_big,
                      (255, 240, 120), True)
        if self.state == "pause":
            self.draw_overlay("PAUSED", "Press P to continue")
        elif self.state == "gameover":
            self.draw_overlay("GAME OVER", "Score %d   -   ENTER for title" % self.score, (255, 90, 90))
        elif self.state == "win":
            self.draw_overlay("YOU WIN!", "Final score %d   -   ENTER for title" % self.score)
        elif self.state == "clear" and self.phase >= 2:
            self.text("COURSE CLEAR!", SCREEN_W // 2, SCREEN_H // 2 - 40, self.font_big, (255, 240, 120), True)

    # ------------------------------------------------------ main loop
    def handle_key(self, key):
        if key == pygame.K_F11:                       # fullscreen <-> window
            pygame.display.toggle_fullscreen()
            return
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.state == "title":
                self.new_game()
            elif self.state in ("gameover", "win"):
                self.state = "title"
        elif key == pygame.K_p:
            if self.state == "play":
                self.state = "pause"
                MUSIC.pause()
                if pygame.mixer.get_init():
                    pygame.mixer.pause()
            elif self.state == "pause":
                self.state = "play"
                MUSIC.resume()
                if pygame.mixer.get_init():
                    pygame.mixer.unpause()
        elif self.state == "play" and key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w, pygame.K_z):
            self.player.buf = JUMP_BUFFER

    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000, 1 / 30)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
                if ev.type == pygame.KEYDOWN:
                    self.handle_key(ev.key)
            if self.state != "pause":
                self.update(dt)
            self.draw()
            pygame.display.flip()


if __name__ == "__main__":
    Game().run()
