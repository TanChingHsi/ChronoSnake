# ChronoSnake

ChronoSnake is a single-player arcade snake game with a rewind mechanic and
timed bombs. It is intended for players who enjoy quick, keyboard-controlled
arcade games and want to balance growing their snake against the risk of
rewinding or letting a bomb fuse expire.

## How to play

Guide the snake around the board, collect white dots to grow and earn points.\


Hold the left mouse button to use **Redline**:\
the snake fast-forwards while burning one segment per rewind interval. Every\
five segments burned during Redline also spawns a golden snitch, which can be\
collected by any part of the snake while Redline is active. Outside Redline,\
golden snitches can be collected by the front third of the snake. Each golden\
snitch grants 15 length.

Hold **Space** to rewind time by shortening yourself. Rewinding removes\
length. Every 15 length units rewound spawns a moving magenta Dead\
Ringer cube that moves twice as fast as a golden snitch. Eating it\
makes the snake's white segments blink magenta and white and grants a five-second death rewind.\
Each additional Dead Ringer adds another five seconds to the rewind. If the\
snake dies, its defies death and rewinds to the saved state of however many stored seconds prior to death.\
\
\
Collect a white dot while it is flashing to trigger **Clutch**: a parry mechanic that doubles the
snake's current length.\

Each white dot has a 7-second fuse. When it expires, the bomb removes at least\
10 segments or half the snake's length (rounded up), whichever is greater. If\
the snake is shorter than 10 when a bomb expires, the run ends immediately.\

## Controls

- **WASD** or **arrow keys**: move
- **Space** (hold): rewind
- **Left mouse button** (hold): Chase / Redline
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
