from utils.constants import ROWS, COLS
from pyglet.gl import glBindBufferBase, GL_SHADER_STORAGE_BUFFER, GL_NEAREST
import pyglet

shader_source = f"""#version 430 core

layout(std430, binding = 3) buffer CellGridIn {{
    int cell_grid_in[{ROWS * COLS}];
}};

layout(std430, binding = 4) buffer CellGridOut {{
    int cell_grid_out[{ROWS * COLS}];
}};

uniform int mouse_row;
uniform int mouse_col;
uniform int mouse_interaction;
uniform int rows;
uniform int cols;
uniform bool running;

layout (local_size_x = 1, local_size_y = 1, local_size_z = 1) in;
layout(location = 0, rgba32f) uniform image2D img_output;

void main() {{
    ivec2 texel_coord = ivec2(gl_GlobalInvocationID.xy);

    int row = texel_coord.y * rows / imageSize(img_output).y;
    int col = texel_coord.x * cols / imageSize(img_output).x;
    int current_index = (row * cols) + col;
    int next = 0;
    int alive_neighbors = 0;
    int mouse_interaction_index = (mouse_row * cols) + mouse_col;

    if (mouse_interaction != -1 && current_index == mouse_interaction_index) {{
        next = mouse_interaction;
    }}
    else if (!running) {{
        next = cell_grid_in[current_index];
    }}
    else {{
        for (int dy = -1; dy <= 1; dy++) {{
            for (int dx = -1; dx <= 1; dx++) {{
                if (dx == 0 && dy == 0) continue;

                int nx = texel_coord.x + dx;
                int ny = texel_coord.y + dy;
                if (nx >= 0 && nx < cols && ny >= 0 && ny < rows) {{
                    int neighbor_index = ny * cols + nx;
                    alive_neighbors += cell_grid_in[neighbor_index];
                }}
            }}
        }}

        if (cell_grid_in[current_index] == 0 && alive_neighbors == 3) {{
            next = 1;
        }}
        else if (cell_grid_in[current_index] == 1 && (alive_neighbors == 3 || alive_neighbors == 2)) {{
            next = 1;
        }}  
    }}

    vec4 value;
    if (next == 1) {{
        value = vec4(1.0, 1.0, 1.0, 1.0);
    }}
    else {{
        value = vec4(0.19, 0.31, 0.31, 1.0);
    }}

    cell_grid_out[current_index] = next;

    imageStore(img_output, texel_coord, value);
}}
"""

def create_shader(grid):
    shader_program = pyglet.graphics.shader.ComputeShaderProgram(shader_source)

    game_of_life_image = pyglet.image.Texture.create(COLS, ROWS, internalformat=pyglet.gl.GL_RGBA32F, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)

    uniform_location = shader_program['img_output']
    game_of_life_image.bind_image_texture(unit=uniform_location)

    ssbo_in = pyglet.graphics.BufferObject(len(grid) * 4, usage=pyglet.gl.GL_DYNAMIC_COPY)
    ssbo_out = pyglet.graphics.BufferObject(len(grid) * 4, usage=pyglet.gl.GL_DYNAMIC_COPY)
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, ssbo_in.id)
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 4, ssbo_out.id)

    return shader_program, game_of_life_image, ssbo_in, ssbo_out