#!/usr/bin/env python3
"""
JERBOA — unicode terminal edition 🦕
SPACE / ↑  to jump  │  R  to restart  │  Q  to quit
"""

import time
import random
import sys

try:
    from blessed import Terminal
except ImportError:
    sys.exit("Missing dependency — run:  pip install blessed")

# ── Config ────────────────────────────────────────────────────────────────────

FPS       = 22
JERBOA_COL  = 8          # fixed horizontal column of the jerboa
GRAVITY   = 0.50       # downward acceleration in sub-pixels / frame²
JUMP_VEL  = -3.8       # initial upward velocity in sub-pixels / frame
SUB       = 2.0        # sub-pixels per terminal row (sub-pixel precision)
BASE_SPD  = 0.84       # starting cactus speed in cols / frame
ACCEL     = 0.00048    # speed increase per frame

# Frames the jerboa spends airborne — sets the minimum cactus spacing so a jump
# arc can complete before the next obstacle arrives.
JUMP_AIR_FRAMES = 2.0 * abs(JUMP_VEL) / GRAVITY
RAMP_FRAMES     = 4000    # frames over which spacing tightens to the floor

# ── Sprites ───────────────────────────────────────────────────────────────────
# Each sprite is a list of strings, top row first.

JERBOA_W = 4
JERBOA_H = 3

JERBOA_A = [             # running — right foot forward
    " ▄█▖",
    "▐██▌",
    " ▘▝ ",
]
JERBOA_B = [             # running — left foot forward
    " ▄█▖",
    "▐██▌",
    " ▝▘ ",
]
JERBOA_AIR = [           # airborne
    " ▄█▖",
    "▐██▌",
    "    ",
]
JERBOA_DEAD = [          # collision — eye turns to ×
    " ▄█▖",
    "▐×█▌",
    " ▘▘ ",
]

# Cactus variants: (width, lines_top_to_bottom)
CACTI = [
    (2, [
        "▟▙",
        "██",
    ]),
    (3, [
        " █ ",
        "▟█▙",
        " █ ",
    ]),
    (3, [
        "▗█▖",
        "▙█▟",
        " █ ",
    ]),
]

# ── Roadrunner (flying enemy) ─────────────────────────────────────────────────

ROADRUNNER_W       = 5
ROADRUNNER_H       = 2
ROADRUNNER_SPEED   = 0.45   # cols / frame, independent of world scroll
ROADRUNNER_ALT     = 6      # rows above the ground for the sprite's top
ROADRUNNER_RESPAWN = 66     # frames before a stomped bird returns (~3s @ 22fps)

ROADRUNNER_A = [            # wings up
    "▘▄█▄▝",
    " ▀▀▀ ",
]
ROADRUNNER_B = [            # wings down
    " ▄█▄ ",
    "▖▀▀▀▗",
]


# ── Game state ────────────────────────────────────────────────────────────────

class State:
    def __init__(self, h: int, w: int, hi_score: int = 0, birds_killed: int = 0):
        self.h            = h
        self.w            = w
        self.ground       = h - 4      # row index of the ground line
        self.hi_score     = hi_score
        self.birds_killed = birds_killed  # session-wide total, persists across restarts

        # jerboa physics (sub-pixel space)
        self._floor   = float((self.ground - JERBOA_H) * SUB)
        self.jerboa_py  = self._floor    # sub-pixel y position of jerboa top
        self.jerboa_vy  = 0.0
        self.jumping  = False

        # game progress
        self.alive    = True
        self.score    = 0
        self.frame    = 0
        self.anim     = 0              # 0 or 1, alternates for leg animation
        self.speed    = BASE_SPD

        # obstacles
        self.cacti    = []             # [[x_float, width, lines], ...]
        self.spawn_in = random.randint(35, 65)

        # roadrunner — bounces between screen edges, deadly on side/bottom
        # contact, despawns if stomped from above, respawns on the right
        self.rr_x       = float(max(0, w - ROADRUNNER_W))
        self.rr_dx      = -1.0
        self.rr_alive   = True
        self.rr_respawn = 0       # frames until a stomped bird returns

    @property
    def jerboa_row(self) -> int:
        """Top terminal row of the jerboa sprite."""
        return int(self.jerboa_py / SUB)

    def jump(self):
        if not self.jumping and self.alive:
            self.jumping = True
            self.jerboa_vy = JUMP_VEL

    def update(self):
        if not self.alive:
            return

        self.frame += 1
        self.score += 1
        self.speed  = BASE_SPD + self.frame * ACCEL

        # ── jerboa physics ──────────────────────────────────────────────────────
        if self.jumping:
            self.jerboa_py += self.jerboa_vy
            self.jerboa_vy += GRAVITY
            if self.jerboa_py >= self._floor:
                self.jerboa_py = self._floor
                self.jerboa_vy = 0.0
                self.jumping = False

        # ── leg animation (alternates every 5 frames) ─────────────────────────
        if self.frame % 5 == 0:
            self.anim ^= 1

        # ── move cacti ────────────────────────────────────────────────────────
        for c in self.cacti:
            c[0] -= self.speed
        self.cacti = [c for c in self.cacti if c[0] + c[1] > 0]

        # ── spawn new cactus ──────────────────────────────────────────────────
        # Spacing is measured in cols (not frames) so the jumpable floor stays
        # constant regardless of speed. Max spacing shrinks toward the floor as
        # the run progresses → more cacti over time.
        self.spawn_in -= 1
        if self.spawn_in <= 0:
            min_cols = JUMP_AIR_FRAMES * self.speed * 1.3   # 30% margin
            progress = min(1.0, self.frame / RAMP_FRAMES)
            max_cols = min_cols * (3.0 - 2.0 * progress)    # 3x → 1x
            gap_cols = random.uniform(min_cols, max_cols)
            self.spawn_in = max(1, int(gap_cols / self.speed))
            vi = random.randint(0, len(CACTI) - 1)
            cw, cl = CACTI[vi]
            self.cacti.append([float(self.w - 1), cw, cl])

        # ── roadrunner movement / respawn ────────────────────────────────────
        if self.rr_alive:
            self.rr_x += self.rr_dx * ROADRUNNER_SPEED
            if self.rr_x <= 0:
                self.rr_x  = 0.0
                self.rr_dx = 1.0
            elif self.rr_x + ROADRUNNER_W >= self.w:
                self.rr_x  = float(self.w - ROADRUNNER_W)
                self.rr_dx = -1.0
        else:
            self.rr_respawn -= 1
            if self.rr_respawn <= 0:
                self.rr_alive = True
                self.rr_x     = float(max(0, self.w - ROADRUNNER_W))
                self.rr_dx    = -1.0     # heads left from the right edge

        # ── collision (AABB with small inset for fairness) ────────────────────
        dr     = self.jerboa_row
        d_left = JERBOA_COL + 1          # 1-col inset on left
        d_right= JERBOA_COL + JERBOA_W - 1 # 1-col inset on right
        d_top  = dr + 1                # skip very top row (head is small)
        d_bot  = dr + JERBOA_H - 1

        for cx, cw, cl in self.cacti:
            ci    = int(cx)
            c_top = self.ground - len(cl)
            c_bot = self.ground - 1
            if (d_right > ci and d_left < ci + cw and
                    d_top <= c_bot and d_bot >= c_top):
                self.alive    = False
                self.hi_score = max(self.hi_score, self.score)
                break

        # roadrunner — stomp from above kills the bird; any other contact kills
        # the jerboa
        if self.alive and self.rr_alive:
            rr_left  = int(self.rr_x)
            rr_right = rr_left + ROADRUNNER_W
            rr_top   = self.ground - ROADRUNNER_ALT
            rr_bot   = rr_top + ROADRUNNER_H - 1
            if (d_right > rr_left and d_left < rr_right and
                    d_top <= rr_bot and d_bot >= rr_top):
                # Stomp = descending AND jerboa's bottom edge entered from the top
                if self.jerboa_vy > 0 and d_bot <= rr_top + 1:
                    self.rr_alive     = False
                    self.rr_respawn   = ROADRUNNER_RESPAWN
                    self.jerboa_vy      = JUMP_VEL * 0.7  # small bounce off the bird
                    self.birds_killed += 1
                else:
                    self.alive    = False
                    self.hi_score = max(self.hi_score, self.score)


# ── Renderer ──────────────────────────────────────────────────────────────────

def render(state: State, term: Terminal):
    t   = term
    g   = state.ground
    w   = state.w
    buf = []

    # Base rows: just spaces + the ground line. Jerboa and cacti are drawn as
    # colored overlays on top so they can be styled independently.
    rows = [list(" " * w) for _ in range(g + 2)]
    rows[g] = list("─" * w)

    # ── flush base rows with yellow background ───────────────────────────────
    for y, row in enumerate(rows):
        buf.append(t.move(y, 0) + t.on_black + "".join(row)[:w] + t.normal)

    # ── jerboa (teal overlay) ──────────────────────────────────────────────────
    if not state.alive:
        spr = JERBOA_DEAD
    elif state.jumping:
        spr = JERBOA_AIR
    else:
        spr = JERBOA_A if state.anim == 0 else JERBOA_B

    for i, line in enumerate(spr):
        row = state.jerboa_row + i
        if 0 <= row < len(rows):
            buf.append(t.move(row, JERBOA_COL) + t.on_black + t.cyan + line + t.normal)

    # ── cacti (green overlay) ────────────────────────────────────────────────
    for cx, _, cl in state.cacti:
        ci      = int(cx)
        top_row = g - len(cl)
        for i, line in enumerate(cl):
            row = top_row + i
            if row < 0 or row >= len(rows):
                continue
            start = max(0, -ci)
            end   = min(len(line), w - ci)
            if end > start:
                buf.append(t.move(row, ci + start) + t.on_black + t.green + line[start:end] + t.normal)

    # ── roadrunner (magenta overlay, wing-flap animated) ─────────────────────
    if state.rr_alive:
        rr_spr = ROADRUNNER_A if (state.frame // 4) % 2 == 0 else ROADRUNNER_B
        rr_col = int(state.rr_x)
        rr_top = g - ROADRUNNER_ALT
        for i, line in enumerate(rr_spr):
            row = rr_top + i
            if 0 <= row < len(rows):
                start = max(0, -rr_col)
                end   = min(len(line), w - rr_col)
                if end > start:
                    buf.append(t.move(row, rr_col + start) + t.on_black + t.bright_magenta + line[start:end] + t.normal)

    # ── HUD ──────────────────────────────────────────────────────────────────
    tip = "JERBOA  │  SPACE/↑ jump  │  Q quit"
    hud = f"HI {state.hi_score:05d}  {state.score:05d}  "
    buf.append(t.move(0, 0) + t.on_black + t.dim + tip[:w] + t.normal)
    buf.append(t.move(0, max(0, w - len(hud))) + t.on_black + t.bold + hud + t.normal)

    # ── game-over overlay ────────────────────────────────────────────────────
    if not state.alive:
        title  = " ▐ GAME OVER ▌ "
        stats  = f" Distance: {state.score}   Birds: {state.birds_killed} "
        prompt = " R = restart   Q = quit "
        gy     = max(0, g // 2 - 1)
        for offset, line in enumerate((title, stats, prompt)):
            gx = max(0, (w - len(line)) // 2)
            buf.append(t.move(gy + offset, gx) + t.on_black + t.bold + t.red + line + t.normal)

    sys.stdout.write("".join(buf))
    sys.stdout.flush()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    term = Terminal()

    with term.fullscreen(), term.hidden_cursor(), term.cbreak():
        hi_score = 0
        state    = State(term.height, term.width, hi_score)
        sys.stdout.write(term.on_black + term.clear())

        next_tick = time.perf_counter()

        while True:
            # Non-blocking key read
            key = term.inkey(timeout=0)
            if key:
                k = str(key).lower()
                if k == "q":
                    break
                if k == "r" and not state.alive:
                    state = State(term.height, term.width,
                                  state.hi_score, state.birds_killed)
                    sys.stdout.write(term.on_black + term.clear())
                if str(key) == " " or getattr(key, "name", None) == "KEY_UP":
                    state.jump()

            # Fixed-timestep game loop
            now = time.perf_counter()
            if now >= next_tick:
                next_tick = now + 1.0 / FPS
                state.update()
                render(state, term)

    # Clean up terminal on exit
    sys.stdout.write(term.normal + term.clear())
    print("Thanks for playing! 🦕")


if __name__ == "__main__":
    main()
