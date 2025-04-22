import arcade, arcade.gui, random, math, copy, time, json
from utils.constants import COLS, ROWS, CELL_SIZE, SPACING, NEIGHBORS, button_style
from utils.preload import create_sound, destroy_sound, button_texture, button_hovered_texture

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
        self.last_create_sound = time.perf_counter()

        self.start_x = self.window.width / 2 - ((COLS * (CELL_SIZE + SPACING)) / 2)
        self.start_y = self.window.height / 2 - ((ROWS * (CELL_SIZE + SPACING)) / 2)

        with open("settings.json", "r") as file:
            self.settings_dict = json.load(file)

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

        self.back_button = arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='<--', style=button_style, width=100, height=50)
        self.back_button.on_click = lambda e: self.main_exit()
        self.anchor.add(self.back_button, anchor_x="left", anchor_y="top", align_x=5, align_y=-5)

        arcade.schedule(self.update_generation, 1 / self.generation_fps)

    def main_exit(self):
        from menus.main import Main
        self.window.show_view(Main(self.pypresence_client))

    def setup_grid(self, randomized=False):
        self.spritelist.clear()

        self.cell_grid = {}
        self.sprite_grid = {}

        for row in range(ROWS):
            self.cell_grid[row] = {}
            self.sprite_grid[row] = {}
            for col in range(COLS):
                if randomized and random.randint(0, 1) == 1:
                    cell = arcade.SpriteSolidColor(CELL_SIZE, CELL_SIZE, center_x=self.start_x + col * (CELL_SIZE + SPACING), center_y=self.start_y + row * (CELL_SIZE + SPACING), color=arcade.color.WHITE)
                    self.cell_grid[row][col] = 1
                    self.sprite_grid[row][col] = cell
                    self.spritelist.append(cell)

                    self.population += 1

                    continue

                self.cell_grid[row][col] = 0
                cell = arcade.SpriteSolidColor(CELL_SIZE, CELL_SIZE, center_x=self.start_x + col * (CELL_SIZE + SPACING), center_y=self.start_y + row * (CELL_SIZE + SPACING), color=arcade.color.WHITE)
                cell.visible = False
                self.sprite_grid[row][col] = cell
                self.spritelist.append(cell)

    def update_generation(self, _):
        if self.window.keyboard[arcade.key.UP] or self.window.keyboard[arcade.key.DOWN]: # type: ignore
            self.generation_fps += 1 if self.window.keyboard[arcade.key.UP] else -1 # type: ignore
            if self.generation_fps < 1:
                self.generation_fps = 1
            self.fps_label.text = f"FPS: {self.generation_fps}"

            arcade.unschedule(self.update_generation)
            arcade.schedule(self.update_generation, 1 / self.generation_fps)

        if self.window.mouse[arcade.MOUSE_BUTTON_LEFT]: # type: ignore
            grid_col = math.ceil((self.window.mouse.data["x"] - self.start_x + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore
            grid_row = math.ceil((self.window.mouse.data["y"] - self.start_y + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore

            if grid_col < 0 or grid_row < 0 or grid_row >= ROWS or grid_col >= COLS:
                return

            if self.cell_grid[grid_row][grid_col] == 0:
                self.population += 1

                if time.perf_counter() - self.last_create_sound >= 0.05:
                    self.last_create_sound = time.perf_counter()
                    if self.settings_dict.get("sfx", True):
                        create_sound.play(volume=self.settings_dict.get("sfx_volume", 50) / 100)

                self.sprite_grid[grid_row][grid_col].visible = True
                self.cell_grid[grid_row][grid_col] = 1

        elif self.window.mouse[arcade.MOUSE_BUTTON_RIGHT]: # type: ignore
            grid_col = math.ceil((self.window.mouse.data["x"] - self.start_x + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore
            grid_row = math.ceil((self.window.mouse.data["y"] - self.start_y + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore

            if grid_col < 0 or grid_row < 0 or grid_row >= ROWS or grid_col >= COLS:
                return

            if self.cell_grid[grid_row][grid_col] == 1:
                self.population -= 1
                if self.settings_dict.get("sfx", True):
                    destroy_sound.play(volume=self.settings_dict.get("sfx_volume", 50) / 100)
                self.sprite_grid[grid_row][grid_col].visible = False
                self.cell_grid[grid_row][grid_col] = 0

        if self.running:
            self.generation += 1

            self.pypresence_generation_count += 1

            if self.pypresence_generation_count == self.generation_fps * 3:
                self.pypresence_generation_count = 0
                self.pypresence_client.update(state='In Game', details=f'Generation: {self.generation} Population: {self.population}', start=self.pypresence_client.start_time)

            next_grid = copy.deepcopy(self.cell_grid) # create a copy of the old grid so we dont modify it in-place

            grid = self.cell_grid

            for x in range(0, COLS):
                for y in range(0, ROWS):
                    cell_neighbors = 0
                    for neighbor_y, neighbor_x in NEIGHBORS:
                        if neighbor_x == 0 and neighbor_y == 0:
                            continue

                        if grid.get(y + neighbor_y, {}).get(x + neighbor_x) == 1:
                            cell_neighbors += 1

                    if grid[y][x] == 1:
                        if (cell_neighbors == 2 or cell_neighbors == 3):
                            pass # survives
                        else: # dies
                            self.population -= 1
                            self.sprite_grid[y][x].visible = False
                            next_grid[y][x] = 0

                    elif cell_neighbors == 3: # newborn
                        self.population += 1
                        self.sprite_grid[y][x].visible = True
                        next_grid[y][x] = 1

            self.cell_grid = next_grid

            self.population_label.text = f"Population: {self.population}"
            self.generation_label.text = f"Generation: {self.generation}"

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        super().on_key_press(symbol, modifiers)

        if symbol == arcade.key.SPACE:
            self.running = not self.running
        elif symbol == arcade.key.C:
            self.population = 0
            self.generation = 0

            self.population_label.text = f"Population: {self.population}"
            self.generation_label.text = f"Generation: {self.generation}"

            arcade.unschedule(self.update_generation)
            self.setup_grid()
            arcade.schedule(self.update_generation, 1 / self.generation_fps)

    def on_draw(self):
        super().on_draw()

        arcade.draw_rect_outline(arcade.rect.LBWH(self.start_x - (SPACING * 2), self.start_y - (SPACING * 2), COLS * (CELL_SIZE + SPACING), ROWS * (CELL_SIZE + SPACING)), arcade.color.WHITE)

        self.spritelist.draw()
