import arcade, arcade.gui, pyglet, time, json, os

from pyglet.gl import glBindBufferBase, GL_SHADER_STORAGE_BUFFER

from array import array

from utils.constants import COLS, ROWS, button_style
from utils.preload import create_sound, destroy_sound, button_texture, button_hovered_texture, cursor_texture

from game.game_of_life import create_shader
from game.file_support import load_file

class Game(arcade.gui.UIView):
    def __init__(self, pypresence_client=None, generation=None, running=False, cell_grid=None, gps=60, load_from=None):
        super().__init__()

        self.generation = generation or 0
        self.population = 0
        self.running = running or False
        self.cell_grid = cell_grid
        self.load_from = load_from

        self.pypresence_generation_count = 0
        self.gps = gps
        self.generation_time = 1 / self.gps
        self.generation_delta_time = 1 / self.gps

        self.last_generation_update = time.perf_counter()
        self.last_info_update = time.perf_counter()
        self.last_create_sound = time.perf_counter()

        self.has_controller = False
        self.controller_a_press = False
        self.controller_b_press = False

        self.mouse_row = 0
        self.mouse_col = 0
        self.mouse_interaction = -1

        self.pypresence_client = pypresence_client

        with open("settings.json", "r") as file:
            self.settings_dict = json.load(file)

        arcade.schedule(self.update_generation, 1 / self.gps)

    def on_show_view(self):
        super().on_show_view()

        self.setup_game(load_existing=self.cell_grid is not None)

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
            self.spritelist = arcade.SpriteList()
            self.cursor_sprite = arcade.Sprite(cursor_texture)
            self.spritelist.append(self.cursor_sprite)

            self.has_controller = True
            self.controller = self.window.get_controllers()[0]

    def main_exit(self):
        arcade.unschedule(self.update_generation)
        
        self.shader_program.delete()
        self.ssbo_in.delete()
        self.ssbo_out.delete()

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
        if name == "start":
            self.main_exit()
    
    def on_button_release(self, controller, name):
        if name == "a" or name == "b":
            self.mouse_interaction = -1

    def setup_game(self, load_existing=False, randomized=False):
        self.grid = array('i', [0] * ROWS * COLS)

        if self.load_from:
            loaded_positions = load_file(COLS / 2, ROWS / 2, self.load_from)
            
            for row, col in loaded_positions:
                index = (row * COLS) + col
                self.grid[index] = 1

        self.shader_program, self.game_of_life_image, self.ssbo_in, self.ssbo_out = create_shader(self.grid)

        self.ssbo_in.set_data(self.grid.tobytes())

        self.image_sprite = pyglet.sprite.Sprite(img=self.game_of_life_image)
        
        scale_x = (self.window.width * 0.75) / self.image_sprite.width
        scale_y = (self.window.height * 0.75) / self.image_sprite.height
        rendered_width = self.image_sprite.width * scale_x
        rendered_height = self.image_sprite.height * scale_y

        self.image_sprite.scale_x = scale_x 
        self.image_sprite.scale_y = scale_y
        self.image_sprite.x = (self.window.width / 2) - (rendered_width / 2)
        self.image_sprite.y = (self.window.height / 2) - (rendered_height / 2)

        self.grid_outline = pyglet.shapes.BorderedRectangle(
            x=self.image_sprite.x - 3,
            y=self.image_sprite.y - 3,
            width=rendered_width + 5,
            height=rendered_height + 5,
            color=(47, 79, 79, 255),
            border_color=(255, 255, 255, 255),
            border=5
        )

    def update_generation(self, delta_time):
        if self.running:
            self.generation_delta_time = delta_time
            self.generation += 1

        self.pypresence_generation_count += 1

        if self.pypresence_generation_count == self.gps * 3:
            self.pypresence_generation_count = 0
            self.pypresence_client.update(state='In Game', details=f'Generation: {self.generation} Population: {self.population}', start=self.pypresence_client.start_time)

        with self.shader_program:
            self.shader_program['mouse_row'] = self.mouse_row
            self.shader_program['mouse_col'] = self.mouse_col
            self.shader_program['mouse_interaction'] = self.mouse_interaction
            self.shader_program['rows'] = ROWS
            self.shader_program['cols'] = COLS
            self.shader_program['running'] = self.running
            self.shader_program.dispatch(self.game_of_life_image.width, self.game_of_life_image.height, 1, barrier=pyglet.gl.GL_ALL_BARRIER_BITS)

        self.ssbo_in, self.ssbo_out = self.ssbo_out, self.ssbo_in
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, self.ssbo_in.id)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 4, self.ssbo_out.id)

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        super().on_key_press(symbol, modifiers)

        if symbol == arcade.key.SPACE:
            self.running = not self.running
        elif symbol == arcade.key.C:
            self.population = 0
            self.generation = 0

            self.population_label.text = f"Population: {self.population}"
            self.generation_label.text = f"Generation: {self.generation}"
            
            self.grid = array('i', [0] * ROWS * COLS)

            arcade.unschedule(self.update_generation)
            self.setup_game()
            arcade.schedule(self.update_generation, 1 / self.gps)
        elif symbol == arcade.key.R:
            self.population = 0
            self.generation = 0

            self.population_label.text = f"Population: {self.population}"
            self.generation_label.text = f"Generation: {self.generation}"
            
            self.grid = array('i', [0] * ROWS * COLS)

            arcade.unschedule(self.update_generation)
            self.setup_game(randomized=True)
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

        if self.window.mouse[arcade.MOUSE_BUTTON_LEFT] or (self.has_controller and self.controller.a):
            self.mouse_interaction = 1
            self.population += 1

            if time.perf_counter() - self.last_create_sound >= 0.05:
                self.last_create_sound = time.perf_counter()
                if self.settings_dict.get("sfx", True):
                    create_sound.play(volume=self.settings_dict.get("sfx_volume", 50) / 100)
        elif self.window.mouse[arcade.MOUSE_BUTTON_RIGHT] or (self.has_controller and self.controller.b):
            self.mouse_interaction = 0
            self.population -= 1
            if self.settings_dict.get("sfx", True):
                destroy_sound.play(volume=self.settings_dict.get("sfx_volume", 50) / 100)
        else:
            return
            
        start_x, start_y = self.image_sprite.x, self.image_sprite.y
        mouse_x, mouse_y = (self.window.mouse.data.get('x', 0), self.window.mouse.data.get('y', 0)) if not self.has_controller else (self.cursor_sprite.left, self.cursor_sprite.top)
        grid_row = int((mouse_y - start_y) / (self.image_sprite.height / ROWS))
        grid_col = int((mouse_x - start_x) / (self.image_sprite.width / COLS))

        if grid_col < 0 or grid_row < 0 or grid_row >= ROWS or grid_col >= COLS:
            return
        
        self.mouse_row = grid_row
        self.mouse_col = grid_col

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT or button == arcade.MOUSE_BUTTON_RIGHT:
            self.mouse_interaction = -1

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

        self.grid_outline.draw()
        self.image_sprite.draw()

        if self.has_controller:
            self.spritelist.draw()