import math
import random
import struct
import sys

import pygame


SCREEN_WIDTH = 960
SCREEN_HEIGHT = 720
CELL_SIZE = 24
BOARD_LEFT = 24
BOARD_TOP = 112
BOARD_COLUMNS = 38
BOARD_ROWS = 24
BOARD_WIDTH = BOARD_COLUMNS * CELL_SIZE
BOARD_HEIGHT = BOARD_ROWS * CELL_SIZE
MOVE_INTERVAL = 0.12
REWIND_INTERVAL = MOVE_INTERVAL / 2
CHASE_INTERVAL = REWIND_INTERVAL
DEAD_RINGER_REWIND_LENGTH = 15
DEAD_RINGER_REWIND_SECONDS = 5.0
DEAD_RINGER_REWIND_STACK_SECONDS = 5.0
DEAD_RINGER_ANIMATION_SECONDS = 1.6
DEAD_RINGER_FLASH_INTERVAL_MS = 180
DETONATION_FLASH_SECONDS = 0.09
DAMAGE_FLASH_SECONDS = 0.18
SCREEN_SHAKE_SECONDS = 0.16
SCREEN_SHAKE_INTENSITY = 5
CLUTCH_HITSTOP_SECONDS = 0.09
CLUTCH_EFFECT_SECONDS = 0.5
CLUTCH_SHAKE_INTENSITY = 12
GOLD_RADIUS = 9
FOOD_FUSE_SECONDS = 7.0
FOOD_BLINK_SECONDS = 3.0

BACKGROUND = (5, 7, 12)
BOARD_COLOR = (5, 7, 12)
TEXT_COLOR = (245, 247, 250)
MUTED_COLOR = (153, 162, 176)
SNAKE_COLOR = (248, 249, 252)
HEAD_COLOR = (255, 78, 93)
REWIND_COLOR = (215, 220, 228)
FOOD_COLOR = (245, 247, 250)
GOLD_COLOR = (255, 205, 75)
DEAD_RINGER_COLOR = (255, 0, 255)


def display_color(color, rewinding):
    if rewinding:
        gray = sum(color) // 3
        reversed_gray = 255 - gray
        return tuple(round(channel * 0.68 + reversed_gray * 0.32) for channel in color)
    return color


def make_tick_sound():
    sample_rate = 22050
    duration = 0.045
    samples = int(sample_rate * duration)
    data = bytearray()
    for index in range(samples):
        envelope = 1 - index / samples
        value = int(10000 * envelope * math.sin(2 * math.pi * 880 * index / sample_rate))
        data.extend(struct.pack("<h", value))
    return pygame.mixer.Sound(buffer=bytes(data))


class HistoryNode:
    __slots__ = ("value", "previous", "length")

    def __init__(self, value, previous):
        self.value = value
        self.previous = previous
        self.length = 1 + (previous.length if previous is not None else 0)


class RewindHistory:
    __slots__ = ("top",)

    def __init__(self, top=None):
        self.top = top

    def copy(self):
        return RewindHistory(self.top)

    def append(self, value):
        self.top = HistoryNode(value, self.top)

    def pop(self):
        if self.top is None:
            raise IndexError("pop from empty rewind history")
        value = self.top.value
        self.top = self.top.previous
        return value

    def __len__(self):
        return self.top.length if self.top is not None else 0


class CronoSnake:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("CronoSnake")
        self.display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("Consolas", 42, bold=True)
        self.clutch_font = pygame.font.SysFont("Consolas", 72, bold=True)
        self.dead_ringer_font = pygame.font.SysFont("Consolas", 180, bold=True)
        self.font = pygame.font.SysFont("Consolas", 28)
        self.small_font = pygame.font.SysFont("Consolas", 22)
        self.tick_sound = None

        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.tick_sound = make_tick_sound()
        except pygame.error as error:
            print(f"Audio unavailable; rewind will use visual cues only: {error}", file=sys.stderr)

        self.reset()

    def reset(self):
        center_x = BOARD_COLUMNS // 2
        center_y = BOARD_ROWS // 2
        self.snake = [(center_x - offset, center_y) for offset in range(6)]
        self.pending_growth = 0
        self.direction = (1, 0)
        self.direction_changed_since_step = False
        self.history = RewindHistory()
        self.score = 0
        self.white_dots_eaten = 0
        self.dead_ringer_progress = 0
        self.chase_progress = 0
        self.pending_gold = 0
        self.gold = []
        self.dead_ringer_cubes = []
        self.dead_ringer_owned = False
        self.dead_ringer_rewind_seconds = DEAD_RINGER_REWIND_SECONDS
        self.food = self.spawn_food()
        self.food_age = 0.0
        self.food_timer = FOOD_FUSE_SECONDS
        self.game_over = False
        self.won = False
        self.accumulator = 0.0
        self.rewind_sound_timer = 0.0
        self.run_time = 0.0
        self.detonation_flash_timer = 0.0
        self.damage_flash_timer = 0.0
        self.screen_shake_timer = 0.0
        self.hitstop_timer = 0.0
        self.clutch_effect_timer = 0.0
        self.dead_ringer_animation = None
        self.death_history = []
        self.record_death_snapshot()

    @property
    def length(self):
        return len(self.snake) + self.pending_growth

    def spawn_food(self):
        occupied = set(self.snake)
        occupied.update(gold["cell"] for gold in self.gold)
        available = [
            (x, y)
            for x in range(BOARD_COLUMNS)
            for y in range(BOARD_ROWS)
            if (x, y) not in occupied
        ]
        if not available:
            return None
        return random.choice(available)

    def spawn_gold(self):
        while self.pending_gold > 0:
            occupied = set(self.snake)
            if self.food is not None:
                occupied.add(self.food)
            occupied.update(gold["cell"] for gold in self.gold)
            available = [
                (x, y)
                for x in range(BOARD_COLUMNS)
                for y in range(BOARD_ROWS)
                if (x, y) not in occupied
            ]
            if not available:
                return

            cell = random.choice(available)
            angle = random.uniform(0, math.tau)
            speed = random.uniform(150, 210)
            self.gold.append({
                "x": BOARD_LEFT + (cell[0] + 0.5) * CELL_SIZE,
                "y": BOARD_TOP + (cell[1] + 0.5) * CELL_SIZE,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "cell": cell,
            })
            self.pending_gold -= 1

    def spawn_dead_ringer(self):
        occupied = set(self.snake)
        if self.food is not None:
            occupied.add(self.food)
        occupied.update(gold["cell"] for gold in self.gold)
        occupied.update(cube["cell"] for cube in self.dead_ringer_cubes)
        available = [
            (x, y)
            for x in range(BOARD_COLUMNS)
            for y in range(BOARD_ROWS)
            if (x, y) not in occupied
        ]
        if not available:
            return

        cell = random.choice(available)
        angle = random.uniform(0, math.tau)
        speed = random.uniform(300, 420)
        self.dead_ringer_cubes.append({
            "x": BOARD_LEFT + (cell[0] + 0.5) * CELL_SIZE,
            "y": BOARD_TOP + (cell[1] + 0.5) * CELL_SIZE,
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "cell": cell,
        })

    def record_death_snapshot(self):
        state = {
            "snake": list(self.snake),
            "pending_growth": self.pending_growth,
            "direction": self.direction,
            "direction_changed_since_step": self.direction_changed_since_step,
            "history": self.history.copy(),
            "score": self.score,
            "white_dots_eaten": self.white_dots_eaten,
            "dead_ringer_progress": self.dead_ringer_progress,
            "chase_progress": self.chase_progress,
            "pending_gold": self.pending_gold,
            "gold": [gold.copy() for gold in self.gold],
            "dead_ringer_cubes": [cube.copy() for cube in self.dead_ringer_cubes],
            "dead_ringer_owned": self.dead_ringer_owned,
            "dead_ringer_rewind_seconds": self.dead_ringer_rewind_seconds,
            "food": self.food,
            "food_age": self.food_age,
            "food_timer": self.food_timer,
            "game_over": self.game_over,
            "won": self.won,
            "accumulator": self.accumulator,
            "rewind_sound_timer": self.rewind_sound_timer,
            "run_time": self.run_time,
            "detonation_flash_timer": self.detonation_flash_timer,
            "damage_flash_timer": self.damage_flash_timer,
            "screen_shake_timer": self.screen_shake_timer,
            "hitstop_timer": self.hitstop_timer,
            "clutch_effect_timer": self.clutch_effect_timer,
        }
        self.death_history.append((self.run_time, state))

    def start_dead_ringer_rewind(self):
        target_time = self.run_time - self.dead_ringer_rewind_seconds
        snapshot_time, state = self.death_history[0]
        target_index = 0
        for index, (timestamp, candidate) in enumerate(self.death_history):
            if timestamp > target_time:
                break
            snapshot_time, state = timestamp, candidate
            target_index = index

        rewind_states = [
            snapshot
            for timestamp, snapshot in self.death_history[target_index:]
            if timestamp <= self.run_time
        ]
        if not rewind_states:
            rewind_states = [state]
        self.dead_ringer_animation = {
            "states": list(reversed(rewind_states)),
            "elapsed": 0.0,
            "duration": min(
                DEAD_RINGER_ANIMATION_SECONDS,
                max(0.5, len(rewind_states) / 30),
            ),
            "target_time": snapshot_time,
            "target_state": state,
        }
        self.game_over = False
        self.won = False

    def update_dead_ringer_rewind(self, elapsed):
        animation = self.dead_ringer_animation
        if animation is None:
            return

        animation["elapsed"] = min(animation["duration"], animation["elapsed"] + elapsed)
        states = animation["states"]
        progress = animation["elapsed"] / animation["duration"]
        state_index = min(len(states) - 1, int(progress * len(states)))
        state = states[state_index]
        self.snake = list(state["snake"])
        self.pending_growth = state["pending_growth"]
        self.score = state["score"]
        if animation["elapsed"] >= animation["duration"]:
            self.restore_dead_ringer(animation["target_time"], animation["target_state"])
            self.dead_ringer_animation = None

    def restore_dead_ringer(self, snapshot_time, state):
        self.snake = list(state["snake"])
        self.pending_growth = state["pending_growth"]
        self.direction = state["direction"]
        self.direction_changed_since_step = state["direction_changed_since_step"]
        self.history = state["history"].copy()
        self.score = state["score"]
        self.white_dots_eaten = state["white_dots_eaten"]
        self.dead_ringer_progress = state["dead_ringer_progress"]
        self.chase_progress = state["chase_progress"]
        self.pending_gold = state["pending_gold"]
        self.gold = [gold.copy() for gold in state["gold"]]
        self.dead_ringer_cubes = [cube.copy() for cube in state["dead_ringer_cubes"]]
        self.dead_ringer_owned = False
        self.dead_ringer_rewind_seconds = DEAD_RINGER_REWIND_SECONDS
        self.food = state["food"]
        self.food_age = state["food_age"]
        self.food_timer = state["food_timer"]
        self.game_over = False
        self.won = state["won"]
        self.accumulator = state["accumulator"]
        self.rewind_sound_timer = state["rewind_sound_timer"]
        self.run_time = snapshot_time
        self.detonation_flash_timer = state["detonation_flash_timer"]
        self.damage_flash_timer = state["damage_flash_timer"]
        self.screen_shake_timer = state["screen_shake_timer"]
        self.hitstop_timer = state["hitstop_timer"]
        self.clutch_effect_timer = state["clutch_effect_timer"]
        self.death_history = [
            (timestamp, candidate)
            for timestamp, candidate in self.death_history
            if timestamp <= snapshot_time
        ]
    def set_direction(self, direction):
        if (
            not self.direction_changed_since_step
            and direction != (-self.direction[0], -self.direction[1])
        ):
            self.direction = direction
            self.direction_changed_since_step = True

    def update_gold(self, elapsed, chasing=False):
        left = BOARD_LEFT + GOLD_RADIUS
        right = BOARD_LEFT + BOARD_WIDTH - GOLD_RADIUS
        top = BOARD_TOP + GOLD_RADIUS
        bottom = BOARD_TOP + BOARD_HEIGHT - GOLD_RADIUS

        self.spawn_gold()
        for gold in self.gold:
            gold["x"] += gold["vx"] * elapsed
            gold["y"] += gold["vy"] * elapsed
            if gold["x"] < left:
                gold["x"] = left
                gold["vx"] = abs(gold["vx"])
            elif gold["x"] > right:
                gold["x"] = right
                gold["vx"] = -abs(gold["vx"])
            if gold["y"] < top:
                gold["y"] = top
                gold["vy"] = abs(gold["vy"])
            elif gold["y"] > bottom:
                gold["y"] = bottom
                gold["vy"] = -abs(gold["vy"])

            gold["cell"] = (
                int((gold["x"] - BOARD_LEFT) // CELL_SIZE),
                int((gold["y"] - BOARD_TOP) // CELL_SIZE),
            )
        self.collect_touched_gold(chasing)

    def update_dead_ringer(self, elapsed):
        left = BOARD_LEFT + GOLD_RADIUS
        right = BOARD_LEFT + BOARD_WIDTH - GOLD_RADIUS
        top = BOARD_TOP + GOLD_RADIUS
        bottom = BOARD_TOP + BOARD_HEIGHT - GOLD_RADIUS

        for cube in self.dead_ringer_cubes:
            cube["x"] += cube["vx"] * elapsed
            cube["y"] += cube["vy"] * elapsed
            if cube["x"] < left:
                cube["x"] = left
                cube["vx"] = abs(cube["vx"])
            elif cube["x"] > right:
                cube["x"] = right
                cube["vx"] = -abs(cube["vx"])
            if cube["y"] < top:
                cube["y"] = top
                cube["vy"] = abs(cube["vy"])
            elif cube["y"] > bottom:
                cube["y"] = bottom
                cube["vy"] = -abs(cube["vy"])

            cube["cell"] = (
                int((cube["x"] - BOARD_LEFT) // CELL_SIZE),
                int((cube["y"] - BOARD_TOP) // CELL_SIZE),
            )

        for cube in self.dead_ringer_cubes[:]:
            if self.cube_touches_segments(cube, self.snake[:1]):
                if self.dead_ringer_owned:
                    self.dead_ringer_rewind_seconds += DEAD_RINGER_REWIND_STACK_SECONDS
                else:
                    self.dead_ringer_owned = True
                self.dead_ringer_cubes.remove(cube)
                break

    def cube_touches_segments(self, cube, segments):
        radius_squared = GOLD_RADIUS * GOLD_RADIUS
        for cell_x, cell_y in segments:
            left = BOARD_LEFT + cell_x * CELL_SIZE
            top = BOARD_TOP + cell_y * CELL_SIZE
            closest_x = min(max(cube["x"], left), left + CELL_SIZE)
            closest_y = min(max(cube["y"], top), top + CELL_SIZE)
            dx = cube["x"] - closest_x
            dy = cube["y"] - closest_y
            if dx * dx + dy * dy <= radius_squared:
                return True
        return False

    def gold_touches_red_segment(self, gold, chasing=False):
        red_count = max(1, math.ceil(self.length / 3))
        segments = self.snake if chasing else self.snake[:red_count]
        return self.cube_touches_segments(gold, segments)

    def collect_gold(self, gold):
        self.pending_growth += 15
        self.score += 100
        self.gold.remove(gold)

    def collect_touched_gold(self, chasing=False):
        for gold in self.gold[:]:
            if self.gold_touches_red_segment(gold, chasing):
                self.collect_gold(gold)
        self.spawn_gold()

    def update_food_timer(self, elapsed):
        if self.food is None:
            return

        self.food_timer -= elapsed
        self.food_age += elapsed
        if self.food_timer > 0:
            return

        self.detonation_flash_timer = DETONATION_FLASH_SECONDS
        self.damage_flash_timer = DAMAGE_FLASH_SECONDS
        self.screen_shake_timer = SCREEN_SHAKE_SECONDS
        self.food = None
        if self.length < 10:
            self.snake = []
            self.pending_growth = 0
            self.game_over = True
            return

        length_loss = min(self.length, max(10, math.ceil(self.length / 2)))
        pending_loss = min(length_loss, self.pending_growth)
        self.pending_growth -= pending_loss
        body_loss = length_loss - pending_loss
        if body_loss:
            self.snake = self.snake[:-body_loss] if body_loss < len(self.snake) else []
        if self.length == 0:
            self.game_over = True
            return

        self.food = self.spawn_food()
        self.food_age = 0.0
        self.food_timer = FOOD_FUSE_SECONDS
        if self.food is None:
            self.won = True
            self.game_over = True
    def forward_step(self, chasing=False):
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        if not (0 <= new_head[0] < BOARD_COLUMNS and 0 <= new_head[1] < BOARD_ROWS):
            self.game_over = True
            return

        eating_white = new_head == self.food
        clutch = eating_white and self.food_timer <= FOOD_BLINK_SECONDS
        length_before_food = self.length
        tail_will_move = self.pending_growth == 0
        body_to_check = self.snake[1:-1] if tail_will_move and not eating_white else self.snake[1:]
        if new_head in body_to_check:
            self.game_over = True
            return

        self.history.append(tuple(self.snake))
        self.snake.insert(0, new_head)
        if self.pending_growth > 0:
            self.pending_growth -= 1
        else:
            self.snake.pop()
        self.direction_changed_since_step = False

        if eating_white:
            if clutch:
                self.pending_growth = 2 * length_before_food - len(self.snake)
                self.hitstop_timer = CLUTCH_HITSTOP_SECONDS
                self.clutch_effect_timer = CLUTCH_EFFECT_SECONDS
                self.screen_shake_timer = max(self.screen_shake_timer, CLUTCH_EFFECT_SECONDS)
            else:
                self.pending_growth += 2
            self.score += 10
            self.white_dots_eaten += 1
            self.food = self.spawn_food()
            self.food_age = 0.0
            self.food_timer = FOOD_FUSE_SECONDS
            if self.food is None:
                self.won = True
                self.game_over = True
        self.spawn_gold()
        self.collect_touched_gold(chasing)

    def chase_step(self):
        self.forward_step(chasing=True)
        if self.game_over:
            return

        if self.pending_growth > 0:
            self.pending_growth -= 1
        elif self.snake:
            self.snake.pop()

        if not self.snake:
            self.game_over = True
            return

        self.chase_progress += 1
        if self.chase_progress == 5:
            self.chase_progress = 0
            self.pending_gold += 1
            self.spawn_gold()

    def record_rewound_length(self):
        self.dead_ringer_progress += 1
        while self.dead_ringer_progress >= DEAD_RINGER_REWIND_LENGTH:
            self.dead_ringer_progress -= DEAD_RINGER_REWIND_LENGTH
            self.spawn_dead_ringer()

    def rewind_step(self):
        if not self.history:
            return
        self.direction_changed_since_step = False
        if self.length <= 1:
            self.score = max(0, self.score - self.length)
            self.snake = []
            self.pending_growth = 0
            self.game_over = True
            self.record_rewound_length()
            return

        current_head = self.snake[0]
        previous = self.history.pop()
        target_length = self.length - 1
        self.snake = list(previous[:target_length])
        self.pending_growth = target_length - len(self.snake)
        previous_head = self.snake[0]
        reverse_direction = (current_head[0] - previous_head[0], current_head[1] - previous_head[1])
        if reverse_direction != (0, 0):
            self.direction = reverse_direction
        self.score = max(0, self.score - (target_length + 1))
        self.record_rewound_length()

    def draw_text(self, text, position, color, font=None, centered=False, rewinding=False, chasing=False):
        font = font or self.font
        rendered_color = (0, 0, 0) if chasing else display_color(color, rewinding)
        rendered = font.render(text, True, rendered_color)
        rect = rendered.get_rect()
        if centered:
            rect.center = position
        else:
            rect.topleft = position
        self.screen.blit(rendered, rect)

    def draw(self, rewinding, chasing=False):
        color = lambda base: display_color(base, rewinding)
        self.screen.fill((139, 0, 0) if chasing else color(BACKGROUND))
        self.draw_text("[ CRONOSNAKE ]", (BOARD_LEFT, 26), TEXT_COLOR, self.title_font, rewinding=rewinding, chasing=chasing)
        self.draw_text(f"SCORE: {self.score:06d}", (BOARD_LEFT, 70), TEXT_COLOR, rewinding=rewinding, chasing=chasing)
        self.draw_text(f"LEN: {self.length:03d}", (280, 73), MUTED_COLOR, rewinding=rewinding, chasing=chasing)
        dead_ringer_status = (
            f"DR: {self.dead_ringer_rewind_seconds:.0f}S"
            if self.dead_ringer_owned
            else f"DR: {DEAD_RINGER_REWIND_LENGTH - self.dead_ringer_progress} LEFT"
        )
        self.draw_text(
            dead_ringer_status,
            (460, 73),
            MUTED_COLOR,
            rewinding=rewinding,
            chasing=chasing,
        )
        self.draw_text("[SPACE] REWIND", (SCREEN_WIDTH - 225, 73), REWIND_COLOR, rewinding=rewinding, chasing=chasing)

        board_rect = pygame.Rect(BOARD_LEFT, BOARD_TOP, BOARD_WIDTH, BOARD_HEIGHT)
        pygame.draw.rect(self.screen, (110, 0, 0) if chasing else color(BOARD_COLOR), board_rect)
        pygame.draw.rect(self.screen, (0, 0, 0) if chasing else color(TEXT_COLOR), board_rect, 2)

        if self.food is not None:
            food_cube = pygame.Rect(
                BOARD_LEFT + self.food[0] * CELL_SIZE,
                BOARD_TOP + self.food[1] * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
            )
            food_color = SNAKE_COLOR
            if self.food_timer <= FOOD_BLINK_SECONDS:
                blink_phase = 1.5 * self.food_age + 1.4 * self.food_age * self.food_age
                if math.sin(math.tau * blink_phase) > 0:
                    food_color = HEAD_COLOR
            pygame.draw.rect(self.screen, color(food_color), food_cube)

        for gold in self.gold:
            gold_cube = pygame.Rect(
                round(gold["x"] - CELL_SIZE / 2),
                round(gold["y"] - CELL_SIZE / 2),
                CELL_SIZE,
                CELL_SIZE,
            )
            pygame.draw.rect(self.screen, color(GOLD_COLOR), gold_cube)

        for cube in self.dead_ringer_cubes:
            cube_rect = pygame.Rect(
                round(cube["x"] - CELL_SIZE / 2),
                round(cube["y"] - CELL_SIZE / 2),
                CELL_SIZE,
                CELL_SIZE,
            )
            pygame.draw.rect(self.screen, color(DEAD_RINGER_COLOR), cube_rect)

        red_count = max(1, math.ceil(self.length / 3))
        for index, (cell_x, cell_y) in enumerate(self.snake):
            segment = pygame.Rect(
                BOARD_LEFT + cell_x * CELL_SIZE,
                BOARD_TOP + cell_y * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
            )
            if self.dead_ringer_animation is not None:
                segment_color = (
                    DEAD_RINGER_COLOR
                    if pygame.time.get_ticks() // DEAD_RINGER_FLASH_INTERVAL_MS % 2
                    else SNAKE_COLOR
                )
            elif self.damage_flash_timer > 0:
                segment_color = (255, 0, 0)
            elif self.dead_ringer_owned and index >= red_count:
                segment_color = (
                    DEAD_RINGER_COLOR
                    if pygame.time.get_ticks() // 650 % 2
                    else SNAKE_COLOR
                )
            elif chasing:
                segment_color = (255, 255, 255) if pygame.time.get_ticks() // 80 % 2 else (0, 0, 0)
            else:
                segment_color = HEAD_COLOR if index < red_count else SNAKE_COLOR
            pygame.draw.rect(
                self.screen,
                segment_color
                if self.dead_ringer_animation is not None or self.damage_flash_timer > 0 or chasing
                else color(segment_color),
                segment,
            )

        if self.gold:
            self.draw_text(
                f"GOLD x{len(self.gold)}: +15 LEN",
                (BOARD_LEFT, BOARD_TOP + BOARD_HEIGHT + 12),
                GOLD_COLOR,
                self.small_font,
                rewinding=rewinding,
                chasing=chasing,
            )
        else:
            self.draw_text(
                f"GOLD QUEUED: {self.pending_gold}",
                (BOARD_LEFT, BOARD_TOP + BOARD_HEIGHT + 12),
                MUTED_COLOR,
                self.small_font,
                rewinding=rewinding,
                chasing=chasing,
            )
        self.draw_text(
            "[WASD] MOVE",
            (BOARD_LEFT + 300, BOARD_TOP + BOARD_HEIGHT + 12),
            MUTED_COLOR,
            self.small_font,
            rewinding=rewinding,
            chasing=chasing,
        )
        self.draw_text(
            "[HOLD LMB] REDLINE",
            (SCREEN_WIDTH - 240, BOARD_TOP + BOARD_HEIGHT + 12),
            MUTED_COLOR,
            self.small_font,
            rewinding=rewinding,
            chasing=chasing,
        )

        if rewinding:
            ticks = pygame.time.get_ticks()
            flash = 24 + int(20 * (0.5 + 0.5 * math.sin(ticks / 90)))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, flash))
            self.screen.blit(overlay, (0, 0))
            static = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            static_rng = random.Random(ticks // 35)
            for _ in range(18):
                y = static_rng.randrange(BOARD_TOP, BOARD_TOP + BOARD_HEIGHT)
                x = static_rng.randrange(BOARD_LEFT, BOARD_LEFT + BOARD_WIDTH - 48)
                width = static_rng.randrange(12, 72)
                alpha = static_rng.randrange(12, 36)
                pygame.draw.line(static, (220, 225, 235, alpha), (x, y), (x + width, y), 1)
            self.screen.blit(static, (0, 0))

        if rewinding:
            logo_y = BOARD_TOP + BOARD_HEIGHT // 2
            panel = pygame.Rect(0, 0, 144, 96)
            panel.center = (SCREEN_WIDTH // 2, logo_y)
            pygame.draw.rect(self.screen, (9, 12, 18), panel)
            pygame.draw.rect(self.screen, color(REWIND_COLOR), panel, 2)

            arrow_pixels = (
                "...#.",
                "..#..",
                ".#...",
                "#....",
                ".#...",
                "..#..",
                "...#.",
            )
            pixel_size = 8
            glyph_width = len(arrow_pixels[0]) * pixel_size
            glyph_gap = pixel_size * 2
            logo_width = glyph_width * 2 + glyph_gap
            logo_left = SCREEN_WIDTH // 2 - logo_width // 2 + static_rng.choice((-2, -1, 0, 1, 2))
            logo_top = logo_y - len(arrow_pixels) * pixel_size // 2
            ghost = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for arrow_index in range(2):
                arrow_left = logo_left + arrow_index * (glyph_width + glyph_gap)
                for row_index, row in enumerate(arrow_pixels):
                    for column_index, bit in enumerate(row):
                        if bit == "#":
                            pygame.draw.rect(
                                ghost,
                                (145, 165, 190, 75),
                                (
                                    arrow_left + column_index * pixel_size + 3,
                                    logo_top + row_index * pixel_size,
                                    pixel_size,
                                    pixel_size,
                                ),
                            )
            self.screen.blit(ghost, (0, 0))
            for arrow_index in range(2):
                arrow_left = logo_left + arrow_index * (glyph_width + glyph_gap)
                for row_index, row in enumerate(arrow_pixels):
                    for column_index, bit in enumerate(row):
                        if bit == "#":
                            pygame.draw.rect(
                                self.screen,
                                color(TEXT_COLOR),
                                (
                                    arrow_left + column_index * pixel_size,
                                    logo_top + row_index * pixel_size,
                                    pixel_size,
                                    pixel_size,
                                ),
                            )

        if self.game_over:
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            veil.fill((5, 8, 15, 205))
            self.screen.blit(veil, (0, 0))
            if self.won:
                title = "[ BOARD CLEARED ]"
                subtitle = "FILLED THE BOARD. PRESS [R] TO RESTART."
            elif self.length == 0:
                title = "[ LOST TO TIME ]"
                subtitle = "REWIND ERASED THE LAST SEGMENT. PRESS [R]."
            else:
                title = "[ GAME OVER ]"
                subtitle = "PRESS [R] RESTART  /  [ESC] QUIT"
            self.draw_text(title, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 28), TEXT_COLOR, self.title_font, True)
            self.draw_text(subtitle, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 18), MUTED_COLOR, self.font, True)
            elapsed_minutes = int(self.run_time // 60)
            elapsed_seconds = int(self.run_time % 60)
            self.draw_text(
                f"LEN: {self.length:03d}  TIME: {elapsed_minutes:02d}:{elapsed_seconds:02d}",
                (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 62),
                TEXT_COLOR,
                self.font,
                True,
            )

        if self.detonation_flash_timer > 0:
            flash_alpha = round(255 * self.detonation_flash_timer / DETONATION_FLASH_SECONDS)
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, flash_alpha))
            self.screen.blit(flash, (0, 0))

        if self.damage_flash_timer > 0:
            for cell_x, cell_y in self.snake:
                segment = pygame.Rect(
                    BOARD_LEFT + cell_x * CELL_SIZE,
                    BOARD_TOP + cell_y * CELL_SIZE,
                    CELL_SIZE,
                    CELL_SIZE,
                )
                pygame.draw.rect(self.screen, (255, 0, 0), segment)

        if self.clutch_effect_timer > 0:
            flash_alpha = round(170 * self.clutch_effect_timer / CLUTCH_EFFECT_SECONDS)
            clutch_flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            clutch_flash.fill((0, 255, 255, flash_alpha))
            self.screen.blit(clutch_flash, (0, 0))
            clutch_text = self.clutch_font.render("CLUTCH", True, (0, 255, 255))
            clutch_rect = clutch_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(clutch_text, clutch_rect)

        if self.dead_ringer_animation is not None:
            flash_phase = pygame.time.get_ticks() // DEAD_RINGER_FLASH_INTERVAL_MS % 2
            flash_color = (255, 255, 255) if flash_phase else (0, 0, 0)
            text_color = (0, 0, 0) if flash_phase else (255, 255, 255)
            self.screen.fill(flash_color)

            defy = self.dead_ringer_font.render("DEFY", True, text_color)
            defy_box = pygame.Rect(
                BOARD_LEFT + CELL_SIZE,
                BOARD_TOP + BOARD_HEIGHT // 2 - 96,
                BOARD_WIDTH - 2 * CELL_SIZE,
                192,
            )
            self.screen.blit(pygame.transform.smoothscale(defy, defy_box.size), defy_box)

            snake_color = (255, 255, 255) if flash_phase else DEAD_RINGER_COLOR
            for cell_x, cell_y in self.snake:
                segment = pygame.Rect(
                    BOARD_LEFT + cell_x * CELL_SIZE,
                    BOARD_TOP + cell_y * CELL_SIZE,
                    CELL_SIZE,
                    CELL_SIZE,
                )
                pygame.draw.rect(self.screen, snake_color, segment)

        offset_x = 0
        offset_y = 0
        if self.screen_shake_timer > 0:
            shake_intensity = (
                CLUTCH_SHAKE_INTENSITY if self.clutch_effect_timer > 0 else SCREEN_SHAKE_INTENSITY
            )
            offset_x = random.randint(-shake_intensity, shake_intensity)
            offset_y = random.randint(-shake_intensity, shake_intensity)
        self.display.fill(BACKGROUND)
        self.display.blit(self.screen, (offset_x, offset_y))
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            elapsed = min(self.clock.tick(60) / 1000, 0.05)
            hitstopped = self.hitstop_timer > 0
            self.hitstop_timer = max(0.0, self.hitstop_timer - elapsed)
            self.detonation_flash_timer = max(0.0, self.detonation_flash_timer - elapsed)
            self.damage_flash_timer = max(0.0, self.damage_flash_timer - elapsed)
            self.screen_shake_timer = max(0.0, self.screen_shake_timer - elapsed)
            self.clutch_effect_timer = max(0.0, self.clutch_effect_timer - elapsed)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif self.game_over and event.key == pygame.K_r:
                        self.reset()
                    elif not self.game_over:
                        directions = {
                            pygame.K_UP: (0, -1),
                            pygame.K_w: (0, -1),
                            pygame.K_DOWN: (0, 1),
                            pygame.K_s: (0, 1),
                            pygame.K_LEFT: (-1, 0),
                            pygame.K_a: (-1, 0),
                            pygame.K_RIGHT: (1, 0),
                            pygame.K_d: (1, 0),
                        }
                        if event.key in directions:
                            self.set_direction(directions[event.key])

            keys = pygame.key.get_pressed()
            rewinding = (
                keys[pygame.K_SPACE]
                and not self.game_over
                and self.dead_ringer_animation is None
            )
            chasing = (
                pygame.mouse.get_pressed()[0]
                and not self.game_over
                and not rewinding
                and self.dead_ringer_animation is None
            )
            if self.dead_ringer_animation is not None:
                self.update_dead_ringer_rewind(elapsed)
            elif not self.game_over and not hitstopped:
                self.run_time += elapsed
                if rewinding:
                    self.rewind_sound_timer += elapsed
                    if self.rewind_sound_timer >= 0.18:
                        self.rewind_sound_timer = 0.0
                        if self.tick_sound is not None:
                            self.tick_sound.play()
                    self.accumulator += elapsed
                    while self.accumulator >= REWIND_INTERVAL:
                        self.accumulator -= REWIND_INTERVAL
                        self.record_death_snapshot()
                        self.rewind_step()
                        if self.game_over:
                            break
                elif chasing:
                    self.rewind_sound_timer = 0.0
                    self.accumulator += elapsed
                    while self.accumulator >= CHASE_INTERVAL:
                        self.accumulator -= CHASE_INTERVAL
                        self.record_death_snapshot()
                        self.chase_step()
                        if self.game_over:
                            break
                else:
                    self.rewind_sound_timer = 0.0
                    self.accumulator += elapsed
                    while self.accumulator >= MOVE_INTERVAL:
                        self.accumulator -= MOVE_INTERVAL
                        self.record_death_snapshot()
                        self.forward_step()
                        if self.game_over:
                            break
                if not self.game_over:
                    self.update_food_timer(elapsed)
                    self.update_gold(elapsed, chasing)
                    self.update_dead_ringer(elapsed)
                if self.game_over and self.dead_ringer_owned and not self.won:
                    self.start_dead_ringer_rewind()
            self.draw(rewinding, chasing)

        pygame.quit()


if __name__ == "__main__":
    CronoSnake().run()
