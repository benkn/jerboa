# Jerboa

A side-scrolling runner for your terminal. You play a jerboa (a small hopping desert mouse) that jumps over oncoming cacti and deals with a flying roadrunner, all drawn in Unicode block art.

```
  ▟▙▄
▄▟██
  ▖▗
```

## Requirements

- Python 3.8+ (`.mise.toml` pins 3.12)
- A UTF-8 terminal. iTerm2 and the VS Code integrated terminal both work.
- [`blessed`](https://pypi.org/project/blessed/)

## Setup and run

With [mise](https://mise.jdx.dev/), which creates a `.venv` for you:

```sh
mise run init
mise run start
```

Without mise:

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python jerboa.py
```

## Controls

| Key            | Action                                   |
| -------------- | ---------------------------------------- |
| `SPACE` or `↑` | Jump (single jump only)                  |
| `R`            | Restart after game over                  |
| `Q`            | Quit at any time                         |

## How to play

- Cacti scroll in from the right and speed up over time. Jump over them.
- Touching a cactus ends the run.
- The roadrunner flies back and forth overhead. Hitting it from the side or from underneath ends the run.
- Landing on top of the roadrunner stomps it. You get a bounce and a point on the birds-killed counter, and it respawns after about 3 seconds.
- Your score goes up every frame. The hi-score lasts until you quit the game.

## Project layout

- `jerboa.py`: the whole game in a single file, with no build step.
- `REQUIREMENTS.md`: the full spec, covering physics, difficulty scaling, sprites and layout.
- `requirements.txt`: Python dependencies.
- `.mise.toml`: Python version and `init` / `start` tasks.
