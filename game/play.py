import arcade, arcade.gui, random, time, json, os, numpy as np

from utils.constants import COLS, ROWS, CELL_SIZE, SPACING, button_style
from utils.preload import create_sound, destroy_sound, button_texture, button_hovered_texture, cursor_texture

from game.game_of_life import create_numpy_grid, update_generation
from game.file_support import load_file

class Game(arcade.gui.UIView):
    def __init__(self, pypresence_client=None, generation=None, running=False, cell_grid=None, gps=10, load_from=None):
        super().__init__()

        self.generation = generation or 0
        self.population = 0
        self.running = running or False
        self.cell_grid = cell_grid
        self.sprite_grid = {}
        self.load_from = load_from

        self.pypresence_generation_count = 0
        self.gps = gps
        self.generation_time = 1 / self.gps
        self.generation_delta_time = 1 / self.gps
        self.last_generation_update = time.perf_counter()
        self.last_info_update = time.perf_counter()

        self.has_controller = False
        self.controller_a_press = False
        self.controller_b_press = False

        self.pypresence_client = pypresence_client
        self.spritelist = arcade.SpriteList()
        self.last_create_sound = time.perf_counter()

        self.start_x = self.window.width / 2 - ((COLS * (CELL_SIZE + SPACING)) / 2)
        self.start_y = self.window.height / 2 - ((ROWS * (CELL_SIZE + SPACING)) / 2)

        with open("settings.json", "r") as file:
            self.settings_dict = json.load(file)

        arcade.schedule(self.update_generation, 1 / self.gps)

    def on_show_view(self):
        super().on_show_view()

        self.setup_grid(load_existing=self.cell_grid is not None)

        self.anchor = self.add_widget(arcade.gui.UIAnchorLayout(size_hint=(1, 1)))
        self.info_box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=5, vertical=False), anchor_x="center", anchor_y="top")

        self.population_label = arcade.gui.UILabel(text="Population: 0", font_name="Roboto", font_size=16)
        self.info_box.add(self.population_label)

        self.generation_label = arcade.gui.UILabel(text=f"Generation: {self.generation}", font_name="Roboto", font_size=16)
        self.info_box.add(self.generation_label)

        self.fps_label = arcade.gui.UILabel(text=f"Generations/second: {self.gps}", font_name="Roboto", font_size=16)
        self.info_box.add(self.fps_label)

        self.actual_fps_label = arcade.gui.UILabel(text=f"Actual generations/second: 0", font_name="Roboto", font_size=16)
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

        if self.window.get_controllers():
            self.cursor_sprite = arcade.Sprite(cursor_texture)
            self.spritelist.append(self.cursor_sprite)
            self.has_controller = True

    def main_exit(self):
        from menus.main import Main
        self.window.show_view(Main(self.pypresence_client))

    def on_trigger_motion(self, controller, name, value):
        if not value >= 0.9:
            return
        
        if name == "lefttrigger":
            self.load()
        elif name == "righttrigger":
            self.save()

    def on_stick_motion(self, controller, name, value):
        if name == "leftstick":
            value *= 3
            self.cursor_sprite.center_x += value.x
            self.cursor_sprite.center_y += value.y

    def on_button_press(self, controller, name):
        if name == "a":
            self.controller_a_press = True
        elif name == "b":
            self.controller_b_press = True
        elif name == "start":
            self.main_exit()
    
    def on_button_release(self, controller, name):
        if name == "a":
            self.controller_a_press = False
        elif name == "b":
            self.controller_b_press = False

    def setup_grid(self, load_existing=False, randomized=False):
        self.spritelist.clear()

        if self.load_from:
            loaded_data = load_file(COLS / 2, ROWS / 2, self.load_from)

        self.cell_grid = create_numpy_grid()

        for row in range(ROWS):
            self.sprite_grid[row] = {}
            for col in range(COLS):
                if self.load_from:
                    if (row, col) in loaded_data:
                        self.cell_grid[row, col] = 1
                elif not load_existing:
                    if randomized and random.randint(0, 1):
                        self.cell_grid[row, col] = 1

                cell = arcade.SpriteSolidColor(CELL_SIZE, CELL_SIZE, center_x=self.start_x + col * (CELL_SIZE + SPACING), center_y=self.start_y + row * (CELL_SIZE + SPACING), color=arcade.color.WHITE)
                
                if not bool(self.cell_grid[row, col]):
                    cell.visible = False

                self.sprite_grid[row][col] = cell
                self.spritelist.append(cell)

    def update_generation(self, delta_time):
        self.generation_delta_time = delta_time
        
        if self.running:
            self.generation += 1

            self.pypresence_generation_count += 1

            if self.pypresence_generation_count == self.gps * 3:
                self.pypresence_generation_count = 0
                self.pypresence_client.update(state='In Game', details=f'Generation: {self.generation} Population: {self.population}', start=self.pypresence_client.start_time)

            old_grid = self.cell_grid
            self.cell_grid = update_generation(self.cell_grid)

            for row, col in np.argwhere(old_grid != self.cell_grid):
                self.sprite_grid[row][col].visible = bool(self.cell_grid[row, col])

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
            arcade.schedule(self.update_generation, 1 / self.gps)
        elif symbol == arcade.key.R:
            self.population = 0
            self.generation = 0

            self.population_label.text = f"Population: {self.population}"
            self.generation_label.text = f"Generation: {self.generation}"
            
            self.cell_grid = 0
            self.spritelist.clear()
            self.sprite_grid.clear()

            arcade.unschedule(self.update_generation)
            self.setup_grid(randomized=True)
            arcade.schedule(self.update_generation, 1 / self.gps)            

    def on_update(self, delta_time):
        super().on_update(delta_time)
        
        if time.perf_counter() - self.last_info_update >= 0.5:
            self.last_info_update = time.perf_counter()
            self.actual_fps_label.text = f"Actual generations/second: {round(1 / self.generation_delta_time, 2)}"
            if not self.population < 0: # generation might be faster than 60 FPS, leading to minus population counts.
                self.population_label.text = f"Population: {self.population}"
            self.generation_label.text = f"Generation: {self.generation}"

        if self.window.keyboard[arcade.key.UP] or self.window.keyboard[arcade.key.DOWN]: # type: ignore
            self.gps += 1 if self.window.keyboard[arcade.key.UP] else -1 # type: ignore
            
            if self.gps < 1:
                self.gps = 1

            self.generation_time = 1 / self.gps
            self.fps_label.text = f"Generations/second: {self.gps}"

            arcade.unschedule(self.update_generation)
            arcade.schedule(self.update_generation, self.generation_time)

        if self.window.mouse[arcade.MOUSE_BUTTON_LEFT] or self.controller_a_press: # type: ignore
            x = self.window.mouse.data["x"] if not self.controller_a_press else self.cursor_sprite.left
            y = self.window.mouse.data["y"] if not self.controller_a_press else self.cursor_sprite.top       
            grid_col = int((x - self.start_x + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore
            grid_row = int((y - self.start_y + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore

            if grid_col < 0 or grid_row < 0 or grid_row >= ROWS or grid_col >= COLS:
                return
            
            if not self.cell_grid[grid_row, grid_col]:
                self.population += 1

                if time.perf_counter() - self.last_create_sound >= 0.05:
                    self.last_create_sound = time.perf_counter()
                    if self.settings_dict.get("sfx", True):
                        create_sound.play(volume=self.settings_dict.get("sfx_volume", 50) / 100)

                self.sprite_grid[grid_row][grid_col].visible = True
                self.cell_grid[grid_row, grid_col] = 1

        elif self.window.mouse[arcade.MOUSE_BUTTON_RIGHT] or self.controller_b_press: # type: ignore
            x = self.window.mouse.data["x"] if not self.controller_b_press else self.cursor_sprite.left
            y = self.window.mouse.data["y"] if not self.controller_b_press else self.cursor_sprite.top                        
            grid_col = int((x - self.start_x + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore
            grid_row = int((y - self.start_y + (CELL_SIZE / 2)) // (CELL_SIZE + SPACING)) # type: ignore

            if grid_col < 0 or grid_row < 0 or grid_row >= ROWS or grid_col >= COLS:
                return

            if self.cell_grid[grid_row, grid_col]:
                self.population -= 1
                if self.settings_dict.get("sfx", True):
                    destroy_sound.play(volume=self.settings_dict.get("sfx_volume", 50) / 100)
                self.sprite_grid[grid_row][grid_col].visible = False
                self.cell_grid[grid_row, grid_col] = 0

    def load(self):
        arcade.unschedule(self.update_generation)
        from game.file_manager import FileManager
        self.window.show_view(FileManager(os.path.expanduser("~"), [".txt", ".rle"], False, self.pypresence_client, self.generation, self.running, self.cell_grid, self.gps))

    def save(self):
        arcade.unschedule(self.update_generation)
        from game.file_manager import FileManager
        self.window.show_view(FileManager(os.path.expanduser("~"), [".txt", ".rle"], True, self.pypresence_client, self.generation, self.running, self.cell_grid, self.gps))

    def on_draw(self):
        super().on_draw()

        arcade.draw_rect_outline(arcade.rect.LBWH(self.start_x - (SPACING * 2), self.start_y - (SPACING * 2), COLS * (CELL_SIZE + SPACING), ROWS * (CELL_SIZE + SPACING)), arcade.color.WHITE)

        self.spritelist.draw()
