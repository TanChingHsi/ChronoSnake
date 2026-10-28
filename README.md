# CronoSnake

CronoSnake is a single-player arcade snake game with a rewind mechanic. It is
intended for players who enjoy quick, keyboard-controlled arcade games.

## How to play

Guide the snake around the board, collect white dots to grow and earn points,
and hold Space to rewind through previous positions. Rewinding removes
length and score.

## Controls

- WASD or arrow keys move
- Space (hold) rewind
- R restart after the run ends
- Esc quit

Only one direction change is accepted between movement steps, preventing rapid
inputs from reversing the snake into its body.

## Run

Requires Python and Pygame. From the project directory

```powershell
python ChronoSnake.py
```

## Known limitations

- The game is a local, single-player desktop game; it has no multiplayer,
  save system, settings menu, or difficulty selection.
- Rewind audio depends on the system's audio device. If audio cannot be
  initialized, the game reports this and continues with visual rewind cues.
- Movement is grid-based, and only one turn can be made per movement step.