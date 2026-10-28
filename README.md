# ChronoSnake

ChronoSnake is a single-player arcade snake game with a rewind mechanic and
timed bombs. It is intended for players who enjoy quick, keyboard-controlled
arcade games and want to balance growing their snake against the risk of
rewinding or letting a bomb fuse expire.

## How to play

Guide the snake around the board, collect white dots to grow and earn points,
and hold **Space** to rewind through previous positions. Rewinding removes
length and score, but every five segments rewound spawns a bouncing gold dot.
Touch gold with the front third of the snake to gain 15 length and 100 points.

Each white dot has a 7-second fuse. When it expires, the bomb removes at least
10 segments or half the snake's length (rounded up), whichever is greater. If
the snake is shorter than 10 when a bomb expires, the run ends immediately.

## Controls

- **WASD** or **arrow keys**: move
- **Space** (hold): rewind
- **R**: restart after the run ends
- **Esc**: quit

Only one direction change is accepted between movement steps, preventing rapid
inputs from reversing the snake into its body.

## Run

Requires Python and Pygame. From the project directory:

```powershell
python ChronoSnake.py
```

## Known limitations

- The game is a local, single-player desktop game; it has no multiplayer,
  save system, settings menu, or difficulty selection.
- Rewind audio depends on the system's audio device. If audio cannot be
  initialized, the game reports this and continues with visual rewind cues.
- Movement is grid-based, and only one turn can be made per movement step.
