# Development process

## How the idea developed

I have always liked the classic, hungry Snake game, and I had programmed a
version of it in Python in college. I also like Tracer's recall mechanic from Overwatch and the quick back-and-forth of Pong. Those interests gave me a starting point for a fast, familiar arcade game.

I wanted to bring in the high actions-per-minute (APM) feel of games with
risk-and-reward decisions, so I first added bombs. Combining the Snake
starting point with bombs and time manipulation was interesting, but it still
felt boring and the stakes weren't high enough. I changed bomb damage to scale with the snake's length where an expired bomb removes at least 10 segments or half the snake's length, whichever is greater. That made every missed fuse matter more as the snake grew.

I then added a parry mechanic. Parry mechanics seem to appear in every modern
game, and I wanted to give players another way to earn a reward by taking a
risk (successfully collecting a critical bomb grants x2 length). I also implemented a Dead Ringer inspired by the minecraft's totem of undying mechanic mixed with recall, and Redline inspired by Snake.io's rush, tuned for more extreme speed and length consumption. I also decided to increase the speed of length consumption to increase the risk of accidental suicide.

## Playtesting and changes

I asked a gamer friend to play. And I took their tip to implement hitstop on the parry mechanic to make a successful parry have superior visual feedback.

I also asked a non-gamer to play. They suggested making the fuse longer. I
rejected that change because a longer fuse would reduce the time pressure and
kill the tension that the bombs are meant to create.

On a side note (didnt implament this literally) buddys joked that I gotta include an epilepsy warning so I toned down the frequency for rapid screen flashes and dimmed the colors a bit to avoid frying some guys eyes every 3 seconds.

## Tools and credits

I used GitHub Copilot (I believe it auto-routed to GPT-6?) to help implement game features and overhaul the art style. The game began from a tutorial I had followed out of boredom in college. Final iterations of documentations in PROCESS and README are manually typed.

Specifically the tutorial I followed was Kenny Yip Coding's baseline project:
[Kenny Yip Coding — YouTube](https://www.youtube.com/watch?v=FtqWCo1_I4g).
it is credited here as an initial baseline and inspiration for the iterative work.
