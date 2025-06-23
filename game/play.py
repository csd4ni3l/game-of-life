import arcade, arcade.gui, random, time, json, os
from game.file_support import load_file
from utils.constants import COLS, ROWS, CELL_SIZE, SPACING, button_style
from utils.preload import create_sound, destroy_sound, button_texture, button_hovered_texture, NEIGHBOUR_MASKS
from game.game_of_life import get_index, get_bit, get_neighbors, set_bit, unset_bit, create_zeroed_int

class Game(arcade.gui.UIView):
    def __init__(self, pypresence_client=None, generation=None, running=False, cell_grid=None, generation_fps=10, load_from=None):
        super().__init__()

        self.generation = generation or 0
        self.population = 0
        self.running = running or False
        self.cell_grid = cell_grid or 0
        self.sprite_grid = {}
        self.load_from = load_from

        self.pypresence_generation_count = 0
        self.generation_fps = generation_fps
        self.generation_time = 1 / self.generation_fps
        self.generation_delta_time = 1 / self.generation_fps
        self.last_generation_update = time.perf_counter()

        self.pypresence_client = pypresence_client
        self.spritelist = arcade.SpriteList()
        self.last_create_sound = time.perf_counter()

        self.start_x = self.window.width / 2 - ((COLS * (CELL_SIZE + SPACING)) / 2)
        self.start_y = self.window.height / 2 - ((ROWS * (CELL_SIZE + SPACING)) / 2)

        with open("settings.json", "r") as file:
            self.settings_dict = json.load(file)

        arcade.schedule(self.update_generation, 1 / self.generation_fps)

    def on_show_view(self):
        super().on_show_view()
        self.setup_grid(load_existing=bool(self.cell_grid))

        self.anchor = self.add_widget(arcade.gui.UIAnchorLayout(size_hint=(1, 1)))
        self.info_box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=5, vertical=False), anchor_x="center", anchor_y="top")

        self.population_label = arcade.gui.UILabel(text="Population: 0", font_name="Roboto", font_size=16)
        self.info_box.add(self.population_label)

        self.generation_label = arcade.gui.UILabel(text=f"Generation: {self.generation}", font_name="Roboto", font_size=16)
        self.info_box.add(self.generation_label)

        self.fps_label = arcade.gui.UILabel(text=f"FPS: {self.generation_fps}", font_name="Roboto", font_size=16)
        self.info_box.add(self.fps_label)

        self.actual_fps_label = arcade.gui.UILabel(text=f"Actual FPS: 0", font_name="Roboto", font_size=16)
        self.info_box.add(self.actual_fps_label)

        self.back_button = arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='<--', style=button_style, width=100, height=50)
        self.back_button.on_click = lambda event: self.main_exit()
        self.anchor.add(self.back_button, anchor_x="left", anchor_y="top", align_x=5, align_y=-5)

        self.load_button = arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text="Load", style=button_style, width=200, height=100)
        self.load_button.on_click = lambda event: self.load()
        self.anchor.add(self.load_button, anchor_x="left", anchor_y="bottom", align_x=5, align_y=5)

        self.save_button = arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text="Save", style=button_style, width=200, height=100)
        self.save_button.on_click = lambda event: self.save()
        self.anchor.add(self.save_button, anchor_x="right", anchor_y="bottom", align_x=-5, align_y=5)

    def main_exit(self):
        from menus.main import Main
        self.window.show_view(Main(self.pypresence_client))

    def setup_grid(self, load_existing=False, randomized=False):
        self.spritelist.clear()

        if self.load_from:
            loaded_data = load_file(COLS / 2, ROWS / 2, self.load_from)

        self.cell_grid = create_zeroed_int(ROWS * COLS)

        for row in range(ROWS):
            self.sprite_grid[row] = {}
            for col in range(COLS):
                if self.load_from:
                    if (row, col) in loaded_data:
                        self.cell_grid = set_bit(self.cell_grid, get_index(row, col))
                elif not load_existing:
                    if randomized and random.randint(0, 1):
                        self.cell_grid = set_bit(self.cell_grid, get_index(row, col))
                        self.population += 1
                        continue

                cell = arcade.SpriteSolidColor(CELL_SIZE, CELL_SIZE, center_x=self.start_x + col * (CELL_SIZE + SPACING), center_y=self.start_y + row * (CELL_SIZE + SPACING), color=arcade.color.WHITE)
                cell.visible = get_bit(self.cell_grid, get_index(row, col))
                self.sprite_grid[row][col] = cell
                self.spritelist.append(cell)

    def update_generation(self, delta_time):
        self.generation_delta_time = delta_time
        
        if self.running:
            self.generation += 1

            self.pypresence_generation_count += 1

            if self.pypresence_generation_count == self.generation_fps * 3:
                self.pypresence_generation_count = 0
                self.pypresence_client.update(state='In Game', details=f'Generation: {self.generation} Population: {self.population}', start=self.pypresence_client.start_time)

            next_grid = self.cell_grid | 0

            for x in range(0, COLS):
                for y in range(0, ROWS):
                    index = get_index(y, x)
                    cell_neighbors = get_neighbors(self.cell_grid, NEIGHBOUR_MASKS[index])

                    if get_bit(self.cell_grid, index):
                        if (cell_neighbors == 2 or cell_neighbors == 3):
                            pass # survives
                        else: # dies
                            self.population -= 1
                            self.sprite_grid[y][x].visible = False
                            next_grid = unset_bit(next_grid, index)

                    elif cell_neighbors == 3: # newborn
                        self.population += 1
                        self.sprite_grid[y][x].visible = True
                        next_grid = set_bit(next_grid, index)

            self.cell_grid = next_grid

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        super().on_key_press(symbol, modifiers)

        if symbol == arcade.key.SPACE:
            self.running = not self.running
        elif symbol == arcade.key.C:
            self.population = 0
            self.generation = 0

            self.population_label.text = f"Population: {self.population}"
            self.generation_label.text = f"Generation: {self.generation}"
            
            self.cell_grid = 0
            self.spritelist.clear()
            self.sprite_grid.clear()

            arcade.unschedule(self.update_generation)
            self.setup_grid()
            arcade.schedule(self.update_generation, 1 / self.generation_fps)

    def on_update(self, delta_time):
        super().on_update(delta_time)
        
        self.actual_fps_label.text = f"Actual FPS: {round(1 / self.generation_delta_time, 2)}"
        self.population_label.text = f"Population: {self.population}"
        self.generation_label.text = f"Generation: {self.generation}"

        if self.window.keyboard[arcade.key.UP] or self.window.keyboard[arcade.key.DOWN]: # type: ignore
            self.generation_fps += 1 if self.window.keyboard[arcade.key.UP] else -1 # type: ignore
            
            if self.generation_fps < 1:
                self.generation_fps = 1

            self.generation_time = 1 / self.generation_fps
            self.fps_label.text = f"FPS: {self.generation_fps}"

            arcade.unschedule(self.update_generation)
            arcade.schedule(self.update_generation, self.generation_time)

        if self.window.mouse[arcade.MOUSE_BUTTON_LEFT]: # type: ignore
            grid_col = int((self.window.mouse.data["x"] - self.start_x + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore
            grid_row = int((self.window.mouse.data["y"] - self.start_y + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore

            if grid_col < 0 or grid_row < 0 or grid_row >= ROWS or grid_col >= COLS:
                return
            
            index = get_index(grid_row, grid_col)

            if not get_bit(self.cell_grid, index):
                self.population += 1

                if time.perf_counter() - self.last_create_sound >= 0.05:
                    self.last_create_sound = time.perf_counter()
                    if self.settings_dict.get("sfx", True):
                        create_sound.play(volume=self.settings_dict.get("sfx_volume", 50) / 100)

                self.sprite_grid[grid_row][grid_col].visible = True
                self.cell_grid = set_bit(self.cell_grid, index)

        elif self.window.mouse[arcade.MOUSE_BUTTON_RIGHT]: # type: ignore
            grid_col = int((self.window.mouse.data["x"] - self.start_x + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore
            grid_row = int((self.window.mouse.data["y"] - self.start_y + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore

            if grid_col < 0 or grid_row < 0 or grid_row >= ROWS or grid_col >= COLS:
                return

            index = get_index(grid_row, grid_col)

            if get_bit(self.cell_grid, index):
                self.population -= 1
                if self.settings_dict.get("sfx", True):
                    destroy_sound.play(volume=self.settings_dict.get("sfx_volume", 50) / 100)
                self.sprite_grid[grid_row][grid_col].visible = False
                self.cell_grid = unset_bit(self.cell_grid, index)

    def load(self):
        arcade.unschedule(self.update_generation)
        from game.file_manager import FileManager
        self.window.show_view(FileManager(os.path.expanduser("~"), [".txt", ".rle"], False, self.pypresence_client, self.generation, self.running, self.cell_grid, self.generation_fps))

    def save(self):
        arcade.unschedule(self.update_generation)
        from game.file_manager import FileManager
        self.window.show_view(FileManager(os.path.expanduser("~"), [".txt", ".rle"], True, self.pypresence_client, self.generation, self.running, self.cell_grid, self.generation_fps))

    def on_draw(self):
        super().on_draw()

        arcade.draw_rect_outline(arcade.rect.LBWH(self.start_x - (SPACING * 2), self.start_y - (SPACING * 2), COLS * (CELL_SIZE + SPACING), ROWS * (CELL_SIZE + SPACING)), arcade.color.WHITE)

        self.spritelist.draw()
