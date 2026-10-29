# ChronoSnake

ChronoSnake is a single-player arcade snake game with a rewind mechanic and
timed bombs. It is intended for players who enjoy quick, keyboard-controlled
arcade games and want to balance growing their snake against the risk of
rewinding or letting a bomb fuse expire.

## How to play

Guide the snake around the board and collect white dots to grow. Track your
survival time and snake length as measures of progress.


Hold the left mouse button to use **Redline**:
the snake fast-forwards while burning one segment per rewind interval. Every
five segments burned during Redline also spawns a golden snitch, which can be
collected by any part of the snake while Redline is active. Outside Redline,
golden snitches can be collected by the front third of the snake. Each golden
snitch grants 15 length.

Hold **Space** to rewind time by shortening yourself. Rewinding removes
length. Every 15 length units rewound spawns a moving magenta Dead
Ringer cube that moves twice as fast as a golden snitch. Eating it
makes the snake's white segments blink magenta and white and grants a five-second death rewind.
Each additional Dead Ringer adds another five seconds to the rewind. If the
snake dies, its defies death and rewinds to the saved state of however many stored seconds prior to death.


Collect a white dot while it is flashing to trigger **Clutch**: a parry mechanic that doubles the
snake's current length.

Each white dot has a 7-second fuse. When it expires, the bomb removes at least
10 segments or half the snake's length (rounded up), whichever is greater. If
the snake is shorter than 10 when a bomb expires, the run ends immediately.

## Controls

- **WASD** or **arrow keys**: move
- **Space** (hold): rewind
- **Left mouse button** (hold): Chase / Redline
- **R**: restart after the run ends
- **Esc**: quit

Only one direction change is accepted between movement steps, preventing rapid
inputs from reversing the snake into its body.

## Run

### Using Python

Install Pygame and run the game with the same Python interpreter. On Windows,
the Python launcher can select Python 3.13 explicitly:

```powershell
py -3.13 -m pip install pygame
py -3.13 .\ChronoSnake.py
```

### Alternative: using uv on Windows

If you have Python but not `uv`, install `uv` from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Open a new PowerShell window, navigate to the ChronoSnake project folder, and
run:

```powershell
uv run --python 3.13 --with pygame==2.6.1 .\ChronoSnake.py
```

`uv` can download Python 3.13 if needed and installs the pinned Pygame version
in its managed environment. This requires an internet connection and a desktop
environment to open the game window.

## Known limitations

- The game is a local, single-player desktop game; it has no multiplayer,
  save system, settings menu, or difficulty selection.
- Rewind audio depends on the system's audio device. If audio cannot be
  initialized, the game reports this and continues with visual rewind cues.
- Movement is grid-based, and only one turn can be made per movement step.

## Demo



https://github.com/user-attachments/assets/faf03678-1c08-4aa3-b433-c70ce70d839c


