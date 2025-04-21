import arcade, arcade.gui, random, math
from utils.constants import COLS, ROWS, CELL_SIZE, SPACING, NEIGHBORS

class Game(arcade.gui.UIView):
    def __init__(self, pypresence_client=None):
        super().__init__()

        self.generation = 0
        self.population = 0
        self.running = True
        self.generation_fps = 10

        self.pypresence_generation_count = 0

        self.pypresence_client = pypresence_client
        self.spritelist = arcade.SpriteList()

        self.start_x = self.window.width / 2 - (COLS * (CELL_SIZE + SPACING)) / 2 + (CELL_SIZE / 2)
        self.start_y = self.window.height / 2 - (ROWS * (CELL_SIZE + SPACING)) / 2 + (CELL_SIZE / 2)

    def on_show_view(self):
        super().on_show_view()
        self.setup_grid()

        self.anchor = self.add_widget(arcade.gui.UIAnchorLayout(size_hint=(1, 1)))
        self.info_box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=5, vertical=False), anchor_x="center", anchor_y="top")

        self.population_label = arcade.gui.UILabel(text="Population: 0", font_name="Protest Strike", font_size=16)
        self.info_box.add(self.population_label)

        self.generation_label = arcade.gui.UILabel(text="Generation: 0", font_name="Protest Strike", font_size=16)
        self.info_box.add(self.generation_label)

        self.fps_label = arcade.gui.UILabel(text="FPS: 10", font_name="Protest Strike", font_size=16)
        self.info_box.add(self.fps_label)

        arcade.schedule(self.update_generation, 1 / 10)

    def setup_grid(self, randomized=False):
        self.spritelist.clear()

        self.cell_grid = {}

        for row in range(ROWS):
            self.cell_grid[row] = {}
            for col in range(COLS):
                if randomized and random.randint(0, 1) == 1:
                    cell = arcade.SpriteSolidColor(CELL_SIZE, CELL_SIZE, center_x=self.start_x + col * (CELL_SIZE + SPACING), center_y=self.start_y + row * (CELL_SIZE + SPACING), color=arcade.color.WHITE)
                    self.cell_grid[row][col] = cell
                    self.spritelist.append(cell)

                    self.population += 1

                    continue

                self.cell_grid[row][col] = None

    def update_generation(self, _):
        if self.running:
            self.generation += 1

            self.pypresence_generation_count += 1

            if self.pypresence_generation_count == self.generation_fps * 3:
                self.pypresence_generation_count = 0
                self.pypresence_client.update(state='In Game', details=f'Generation: {self.generation} Population: {self.population}', start=self.pypresence_client.start_time)

            for x in range(0, COLS):
                for y in range(0, ROWS):
                    cell_neighbors = 0
                    for neighbor_y in NEIGHBORS:
                        for neighbor_x in NEIGHBORS:
                            if neighbor_x == 0 and neighbor_y == 0:
                                continue

                            if self.cell_grid.get(y + neighbor_y, {}).get(x + neighbor_x) is not None:
                                cell_neighbors += 1

                    if self.cell_grid[y][x] is not None:
                        if (cell_neighbors == 2 or cell_neighbors == 3):
                            pass # survives
                        else: # dies
                            self.population -= 1

                            self.spritelist.remove(self.cell_grid[y][x])
                            del self.cell_grid[y][x]
                            self.cell_grid[y][x] = None

                    elif cell_neighbors == 3: # newborn
                        self.population += 1

                        cell = arcade.SpriteSolidColor(CELL_SIZE, CELL_SIZE, center_x=self.start_x + x * (CELL_SIZE + SPACING), center_y=self.start_y + y * (CELL_SIZE + SPACING), color=arcade.color.WHITE)
                        self.cell_grid[y][x] = cell
                        self.spritelist.append(cell)

            self.population_label.text = f"Population: {self.population}"
            self.generation_label.text = f"Generation: {self.generation}"

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        super().on_key_press(symbol, modifiers)

        if symbol == arcade.key.SPACE:
            self.running = not self.running

    def on_update(self, delta_time: float) -> bool | None:
        super().on_update(delta_time)

        if self.window.keyboard[arcade.key.UP] or self.window.keyboard[arcade.key.DOWN]: # type: ignore
            self.generation_fps += 1 if self.window.keyboard[arcade.key.UP] else -1 # type: ignore
            self.fps_label.text = f"FPS: {self.generation_fps}"

            arcade.unschedule(self.update_generation)
            arcade.schedule(self.update_generation, 1 / self.generation_fps)

        if self.window.mouse[arcade.MOUSE_BUTTON_LEFT]: # type: ignore
            grid_col = math.ceil((self.window.mouse.data["x"] - self.start_x + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore
            grid_row = math.ceil((self.window.mouse.data["y"] - self.start_y + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore

            if self.cell_grid[grid_row][grid_col] is None:
                self.population += 1

                cell = arcade.SpriteSolidColor(CELL_SIZE, CELL_SIZE, center_x=self.start_x + grid_col * (CELL_SIZE + SPACING), center_y=self.start_y + grid_row * (CELL_SIZE + SPACING), color=arcade.color.WHITE)
                self.cell_grid[grid_row][grid_col] = cell
                self.spritelist.append(cell)

    def on_draw(self):
        super().on_draw()

        self.spritelist.draw()
