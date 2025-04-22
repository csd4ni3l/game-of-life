import arcade.color
from arcade.types import Color
from arcade.gui.widgets.buttons import UITextureButtonStyle

COLS = 80
ROWS = 60
CELL_SIZE = 10
SPACING = 2
NEIGHBORS = [(-1, 0), (-1, 1), (-1, -1),(0, 0), (0, 1), (0, -1), (1, 0), (1, 1), (1, -1)]

log_dir = 'logs'
menu_background_color = Color(28, 28, 28)

button_style = {'normal': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK), 'hover': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK),
                'press': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK), 'disabled': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK)}
