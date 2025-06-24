from utils.constants import ROWS, COLS
import numpy as np
                   
def create_numpy_grid():
    return np.zeros((ROWS, COLS), dtype=np.uint8)

def count_neighbors(grid):
    padded = np.pad(grid, pad_width=1, mode='constant', constant_values=0)
    
    neighbors = (
        padded[0:-2, 0:-2] +  # top-left
        padded[0:-2, 1:-1] +  # top
        padded[0:-2, 2:] +    # top-right
        padded[1:-1, 0:-2] +  # left
        padded[1:-1, 2:] +    # right
        padded[2:, 0:-2] +    # bottom-left
        padded[2:, 1:-1] +    # bottom
        padded[2:, 2:]        # bottom-right
    )
    
    return neighbors

def update_generation(cell_grid: np.array):
    neighbors = count_neighbors(cell_grid)
    new_grid = ((cell_grid == 1) & ((neighbors == 2) | (neighbors == 3))) | \
                ((cell_grid == 0) & (neighbors == 3))
    return new_grid.astype(np.uint8)