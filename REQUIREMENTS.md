# Jerboa — Terminal Game Requirements

## Overview
This is a side-scrolling runner game, where the player controls a jerboa (a small hopping desert mouse) that must jump over oncoming cacti while dodging — or stomping — a flying roadrunner. The game runs entirely in the terminal (iTerm2 and VS Code integrated terminal both supported).

## Technology
- **Language:** Python 3.8+
- **Key dependency:** `blessed` (`pip install blessed`)
- **Single file:** `jerboa.py` — no build step, just run it

## Gameplay

### Core loop
- The jerboa stands at a fixed horizontal position on the left side of the screen
- Cacti scroll in from the right at increasing speed
- A roadrunner flies back and forth across the screen at a fixed altitude
- The player presses SPACE or ↑ to make the jerboa jump
- Touching a cactus, or hitting the bird from the side / underneath, ends the run
- Landing on top of the bird stomps it: the bird despawns, the jerboa bounces, and
  the session-wide birds-killed counter goes up
- Score increments every frame; speed increases gradually over time

### Controls
| Key            | Action                                   |
| -------------- | ---------------------------------------- |
| `SPACE` or `↑` | Jump (single jump only — no double jump) |
| `R`            | Restart after game over                  |
| `Q`            | Quit at any time                         |

### Difficulty scaling
- Base speed: 0.84 cols/frame
- Speed increases by 0.00048 per frame (compounding)
- Cactus spacing is computed in **columns**, not frames, so the minimum
  jumpable gap stays consistent at any speed:
  - `min_cols = JUMP_AIR_FRAMES * speed * 1.3` (jump arc + 30% margin)
  - `max_cols` shrinks linearly from `3 × min_cols` → `1 × min_cols` over the
    first 4000 frames of the run (≈ 3 min @ 22 FPS), so density ramps up
    toward the jumpable floor

## Visuals

### Style: Unicode block art
All sprites use Unicode block / quadrant characters (█ ▟ ▙ ▄ ▀ ▐ ▌ ▘ ▝ ▖ ▗ ─ etc.)
for a more polished look over plain ASCII. Terminal must support UTF-8.

### Color scheme
- **Background:** black (`on_black`)
- **Jerboa:** teal / cyan
- **Cacti:** green
- **Roadrunner:** bright magenta
- **Ground line + HUD:** default foreground on black
- **Game-over banner:** bold red on black

### Jerboa sprite (4 wide × 3 tall)
Four states: running-A (right foot), running-B (left foot), airborne, dead.

```
Running A:    Running B:    Airborne:     Dead:
 ▄█▖           ▄█▖           ▄█▖           ▄█▖
▐██▌          ▐██▌          ▐██▌          ▐×█▌
 ▘▝            ▝▘                          ▘▘
```

Leg animation alternates every 5 frames.

### Cactus variants (3 shapes)
```
Small (2×2):   Medium (3×3):   Tall (3×3):
▟▙              █              ▗█▖
██             ▟█▙             ▙█▟
                █               █
```

Cacti are chosen randomly each spawn.

### Roadrunner sprite (5 wide × 2 tall)
Two-frame wing-flap animation, swapped every 4 frames.

```
Wings up:     Wings down:
▘▄█▄▝          ▄█▄
 ▀▀▀         ▖▀▀▀▗
```

### Ground
A continuous `─` line at the bottom of the play area.

### HUD
- Top-left: `JERBOA  │  SPACE/↑ jump  │  Q quit` (dimmed)
- Top-right: `HI XXXXX  XXXXX` (hi-score + current score, bold)
- Mid-screen on game over: three centered lines, bold red on black
  - ` ▐ GAME OVER ▌ `
  - ` Distance: <score>   Birds: <total> `
  - ` R = restart   Q = quit `

## Physics (sub-pixel model)
- Jerboa position stored in sub-pixels (SUB = 2.0 sub-pixels per terminal row)
- Jump initial velocity: −3.8 sub-pixels/frame (upward)
- Gravity: +0.50 sub-pixels/frame² (downward acceleration)
- `JUMP_AIR_FRAMES = 2 * |JUMP_VEL| / GRAVITY` — total frames the jerboa is airborne
- Jerboa lands when sub-pixel position returns to floor; jumping flag cleared
- A successful bird-stomp resets `jerboa_vy` to `JUMP_VEL * 0.7` for a small bounce

## Roadrunner behavior
- Constant horizontal speed (0.45 cols/frame), independent of world scroll
- Bounces between the left and right edges of the screen
- Sprite sits at `ground - 6` (top row), occupies 2 rows
- Altitude overlaps with the upper portion of a jump arc — clear when the jerboa
  is on the ground, but in the way during a jump
- On stomp (jerboa descending AND its bottom edge enters the bird's top row):
  - Bird despawns (movement + render skipped)
  - Jerboa gets a `JUMP_VEL * 0.7` bounce
  - `birds_killed` counter increments
  - Respawn timer starts (66 frames ≈ 3 seconds @ 22 FPS)
  - When the timer expires, the bird reappears at the right edge heading left
- Any other contact (side or underside) ends the run

## Collision detection
- Simple AABB between jerboa hitbox and each cactus / the roadrunner
- Jerboa hitbox is inset by 1 col left/right and 1 row at the top (forgiving feel)
- Cactus / underside-bird collision triggers `alive = False`; hi-score and
  birds-killed are preserved across restarts

## Persistent stats (session-wide, survive `R` restarts)
- `hi_score` — best distance reached in any run this session
- `birds_killed` — total birds stomped across all runs this session

Both are threaded through the `State` constructor on restart and reset only when
the process exits.

## Layout
```
Row 0          : HUD (title left, score right)
Rows 1 – (g-1) : Play area (jerboa + cacti + roadrunner)
Row g          : Ground (─────────────────────────────)
Rows g+1 …     : Blank margin
```
Where `g = terminal_height − 4`.

## Non-requirements (v1)
- No sound
- No clouds or decorative background elements
- No high-score / birds-killed persistence to disk (stats reset on app restart)
- No difficulty levels or settings
- No ducking — bird is dodged only by *not* jumping when it's in your column
