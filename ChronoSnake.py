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


class CronoSnake:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("CronoSnake")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("Consolas", 42, bold=True)
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
        self.history = []
        self.score = 0
        self.white_dots_eaten = 0
        self.rewind_progress = 0
        self.pending_gold = 0
        self.gold = []
        self.food = self.spawn_food()
        self.food_age = 0.0
        self.food_timer = FOOD_FUSE_SECONDS
        self.game_over = False
        self.won = False
        self.accumulator = 0.0
        self.rewind_sound_timer = 0.0

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
    def set_direction(self, direction):
        if (
            not self.direction_changed_since_step
            and direction != (-self.direction[0], -self.direction[1])
        ):
            self.direction = direction
            self.direction_changed_since_step = True

    def update_gold(self, elapsed):
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
        self.collect_touched_gold()

    def gold_touches_red_segment(self, gold):
        red_count = max(1, math.ceil(self.length / 3))
        radius_squared = GOLD_RADIUS * GOLD_RADIUS
        for cell_x, cell_y in self.snake[:red_count]:
            left = BOARD_LEFT + cell_x * CELL_SIZE
            top = BOARD_TOP + cell_y * CELL_SIZE
            closest_x = min(max(gold["x"], left), left + CELL_SIZE)
            closest_y = min(max(gold["y"], top), top + CELL_SIZE)
            dx = gold["x"] - closest_x
            dy = gold["y"] - closest_y
            if dx * dx + dy * dy <= radius_squared:
                return True
        return False

    def collect_gold(self, gold):
        self.pending_growth += 15
        self.score += 100
        self.gold.remove(gold)

    def collect_touched_gold(self):
        for gold in self.gold[:]:
            if self.gold_touches_red_segment(gold):
                self.collect_gold(gold)
        self.spawn_gold()

    def update_food_timer(self, elapsed):
        if self.food is None:
            return

        self.food_timer -= elapsed
        self.food_age += elapsed
        if self.food_timer > 0:
            return

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
    def forward_step(self):
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        if not (0 <= new_head[0] < BOARD_COLUMNS and 0 <= new_head[1] < BOARD_ROWS):
            self.game_over = True
            return

        eating_white = new_head == self.food
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
        self.collect_touched_gold()

    def record_rewound_length(self):
        self.rewind_progress += 1
        if self.rewind_progress == 5:
            self.rewind_progress = 0
            self.pending_gold += 1
            self.spawn_gold()

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

    def draw_text(self, text, position, color, font=None, centered=False, rewinding=False):
        font = font or self.font
        rendered = font.render(text, True, display_color(color, rewinding))
        rect = rendered.get_rect()
        if centered:
            rect.center = position
        else:
            rect.topleft = position
        self.screen.blit(rendered, rect)

    def draw(self, rewinding):
        color = lambda base: display_color(base, rewinding)
        self.screen.fill(color(BACKGROUND))
        self.draw_text("[ CRONOSNAKE ]", (BOARD_LEFT, 26), TEXT_COLOR, self.title_font, rewinding=rewinding)
        self.draw_text(f"SCORE: {self.score:06d}", (BOARD_LEFT, 70), TEXT_COLOR, rewinding=rewinding)
        self.draw_text(f"LEN: {self.length:03d}", (280, 73), MUTED_COLOR, rewinding=rewinding)
        self.draw_text(
            f"GOLD: {5 - self.rewind_progress}",
            (460, 73),
            MUTED_COLOR,
            rewinding=rewinding,
        )
        self.draw_text("[SPACE] REWIND", (SCREEN_WIDTH - 225, 73), REWIND_COLOR, rewinding=rewinding)

        board_rect = pygame.Rect(BOARD_LEFT, BOARD_TOP, BOARD_WIDTH, BOARD_HEIGHT)
        pygame.draw.rect(self.screen, color(BOARD_COLOR), board_rect)
        pygame.draw.rect(self.screen, color(TEXT_COLOR), board_rect, 2)

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

        red_count = max(1, math.ceil(self.length / 3))
        for index, (cell_x, cell_y) in enumerate(self.snake):
            segment = pygame.Rect(
                BOARD_LEFT + cell_x * CELL_SIZE,
                BOARD_TOP + cell_y * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
            )
            segment_color = HEAD_COLOR if index < red_count else SNAKE_COLOR
            pygame.draw.rect(self.screen, color(segment_color), segment)

        if self.gold:
            self.draw_text(
                f"GOLD x{len(self.gold)}: +15 LEN",
                (BOARD_LEFT, BOARD_TOP + BOARD_HEIGHT + 12),
                GOLD_COLOR,
                self.small_font,
                rewinding=rewinding,
            )
        else:
            self.draw_text(
                f"GOLD QUEUED: {self.pending_gold}",
                (BOARD_LEFT, BOARD_TOP + BOARD_HEIGHT + 12),
                MUTED_COLOR,
                self.small_font,
                rewinding=rewinding,
            )
        self.draw_text(
            "[WASD] MOVE",
            (BOARD_LEFT + 300, BOARD_TOP + BOARD_HEIGHT + 12),
            MUTED_COLOR,
            self.small_font,
            rewinding=rewinding,
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

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            elapsed = min(self.clock.tick(60) / 1000, 0.05)
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
            rewinding = keys[pygame.K_SPACE] and not self.game_over
            if not self.game_over:
                if rewinding:
                    self.rewind_sound_timer += elapsed
                    if self.rewind_sound_timer >= 0.18:
                        self.rewind_sound_timer = 0.0
                        if self.tick_sound is not None:
                            self.tick_sound.play()
                    self.accumulator += elapsed
                    while self.accumulator >= REWIND_INTERVAL:
                        self.accumulator -= REWIND_INTERVAL
                        self.rewind_step()
                        if self.game_over:
                            break
                else:
                    self.rewind_sound_timer = 0.0
                    self.accumulator += elapsed
                    while self.accumulator >= MOVE_INTERVAL:
                        self.accumulator -= MOVE_INTERVAL
                        self.forward_step()
                        if self.game_over:
                            break
                if not self.game_over:
                    self.update_food_timer(elapsed)
                    self.update_gold(elapsed)
            self.draw(rewinding)

        pygame.quit()


if __name__ == "__main__":
    CronoSnake().run()
