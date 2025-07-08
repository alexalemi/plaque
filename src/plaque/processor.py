"""Handles the core persistence logic for notebooks."""

from .cell import Cell
from .environment import Environment
from .parser import parse
from .formatter import format

import logging

logger = logging.getLogger(__name__)


class Processor:
    def __init__(self):
        self.environment = Environment()
        self.cells: list[Cell] = []

    def process_cells(self, cells: list[Cell]) -> str:
        # TODO: implement logic, right now full replace
        for cell in cells:
            if cell.is_code:
                self.environment.execute_cell(cell)

        self.cells = cells
        return format(cells)

    def process_file(self, input_path: str) -> str:
        logger.info(f"Processing {input_path}")
        
        with open(input_path, 'r') as f:
            cells = list(parse(f))

        return self.process_cells(cells)

