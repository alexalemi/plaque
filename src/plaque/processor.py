"""Handles the core persistence logic for notebooks."""

from .cell import Cell
from .environment import Environment

import logging

logger = logging.getLogger(__name__)


class Processor:
    def __init__(self):
        self.environment = Environment()
        self.cells: list[Cell] = []

    def process_cells(self, cells: list[Cell]) -> list[Cell]:
        # TODO: implement logic, right now full replace
        for cell in cells:
            if cell.is_code:
                self.environment.execute_cell(cell)

        self.cells = cells
        return cells
