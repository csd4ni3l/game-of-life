from utils.constants import ROWS, COLS, NEIGHBORS
TOTAL_CELLS = ROWS * COLS

def get_index(row, col):
    return row * COLS + col

def get_neighbors(cell_grid, neighbor_mask):
    return (cell_grid & neighbor_mask).bit_count()

def unset_bit(number, i):
    return number & ~(1 << i)

def set_bit(number, i):
    return number | (1 << i)

def get_bit(number, i):
    return (number >> i) & 1

def print_bits(n: int, width: int = 8):
    print(f"{n:0{width}b}")

def create_zeroed_int(n):
    zero_val = 0
    bitmask = (1 << n) -1
    return zero_val & bitmask

def precompute_neighbor_masks():
    masks = [0] * TOTAL_CELLS
    for row in range(ROWS):
        for col in range(COLS):
            index = get_index(row, col)
            mask = 0
            for dy, dx in NEIGHBORS:
                ny, nx = row + dy, col + dx
                if 0 <= ny < ROWS and 0 <= nx < COLS:
                    neighbor_index = get_index(ny, nx)
                    mask |= 1 << neighbor_index
            masks[index] = mask
    return masks