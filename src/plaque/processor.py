"""Handles the core persistence logic for notebooks."""

from .cell import Cell, empty_code_cell
from .environment import Environment

import logging

logger = logging.getLogger(__name__)


class Processor:
    def __init__(self):
        self.environment = Environment()
        self.cells: list[Cell] = []

    def process_cells(self, cells: list[Cell]) -> list[Cell]:
        previous_code_cells = (cell for cell in self.cells if cell.is_code)
        off_script = False
        output = []
        for cell in cells:
            if cell.is_code:
                previous_code_cell = next(previous_code_cells, empty_code_cell)
                if off_script or (cell.content != previous_code_cell.content):
                    # if we've fallen of the script or there is a change in the code, start executing
                    off_script = True
                    self.environment.execute_cell(cell)
                    output.append(cell)
                else:
                    # Copy over the previous result
                    cell.result = previous_code_cell.result
                    cell.error = previous_code_cell.error
                    cell.counter = previous_code_cell.counter
                    output.append(cell)
            else:
                output.append(cell)

        self.cells = output
        return output
