import re

def load_life_6(offset_x, offset_y, data):
    loaded_data = []

    for line in data:
        if line == "#Life 1.06":
            continue

        x, y = line.split(" ")
        x = int(offset_x + int(x))
        y = int(offset_y + int(y))
        loaded_data.append((y, x))

    return loaded_data

def save_life_6(cell_grid):
    data = "#Life 1.06"
    alive_cells = [(row, col) for row in range(len(cell_grid)) for col in range(len(cell_grid[row])) if cell_grid[row][col]]

    for cell in alive_cells:
        data += f"\n{cell[0]} {cell[1]}"

    return data

def load_life_5(offset_x, offset_y, data):
    loaded_data = []

    y = int(offset_y)
    for line in data:
        if line == "#Life 1.05" or line.startswith("#D") or line.startswith("#R") or line.startswith("#N"):
            continue

        y += 1
        for x, cell in enumerate(line):
            x += int(offset_x)
            if cell == "*":
                loaded_data.append((y, x))

    return loaded_data

def save_life_5(cell_grid):
    data = "#Life 1.05\n#D Exported from csd4ni3l's Game Of Life viewer.\n#N\n"

    for row_list in cell_grid.values():
        for cell in row_list.values():
            data += "*" if cell else "."

        data += "\n"

    return data

def load_rle(offset_x, offset_y, data):
    loaded_data = []
    rle_data = ""
    x_offset = int(offset_x)
    y_offset = int(offset_y)
    y = 0
    x = 0

    for line in data:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("x"):
            continue

        rle_data += line

    pattern = re.compile(r"(\d*)([bo$!])")
    matches = pattern.findall(rle_data)

    for count_str, symbol in matches:
        count = int(count_str) if count_str else 1
        if symbol == "b":
            x += count
        elif symbol == "o":
            for _ in range(count):
                loaded_data.append((y_offset + y, x_offset + x))
                x += 1
        elif symbol == "$":
            y += count
            x = 0
        elif symbol == "!":
            break

    return loaded_data

def save_rle(cell_grid):
    live_cells = [(row, col) for row in cell_grid for col in cell_grid[row] if cell_grid[row][col]]

    if not live_cells:
        return "#C Empty pattern\nx = 0, y = 0, rule = B3/S23\n!"

    min_row = min(row for row, _ in live_cells)
    max_row = max(row for row, _ in live_cells)
    min_col = min(col for _, col in live_cells)
    max_col = max(col for _, col in live_cells)

    width = max_col - min_col + 1
    height = max_row - min_row + 1

    data = "#C Exported from csd4ni3l's Game Of Life viewer.\n"
    data += f"x = {width}, y = {height}, rule = B3/S23\n"

    lines = []
    for row in range(min_row, max_row + 1):
        line = ""
        run_char = None
        run_length = 0

        for col in range(min_col, max_col + 1):
            alive = cell_grid.get(row, {}).get(col, False)
            char = "o" if alive else "b"

            if char == run_char:
                run_length += 1
            else:
                if run_char is not None:
                    line += (str(run_length) if run_length > 1 else "") + run_char
                run_char = char
                run_length = 1

        if run_char:
            line += (str(run_length) if run_length > 1 else "") + run_char

        lines.append(line)

    data += "$".join(lines) + "!"

    return data

def load_file(offset_x, offset_y, file_path):
    with open(file_path, "r") as file:
        data = file.read().splitlines()
        if "#Life 1.06" in data:
            return load_life_6(offset_x, offset_y, data)
        elif "#Life 1.05" in data:
            return load_life_5(offset_x, offset_y, data)
        elif file_path.endswith(".rle"):
            return load_rle(offset_x, offset_y, data)

def save_file(cell_grid, file_path, file_type):
    with open(file_path, "w") as file:
        if file_type == "life_6":
            file.write(save_life_6(cell_grid))
        elif file_type == "life_5":
            file.write(save_life_5(cell_grid))
        elif file_type == "rle":
            file.write(save_rle(cell_grid))
