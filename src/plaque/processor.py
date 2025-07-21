"""Handles the core persistence logic for notebooks."""

from typing import Literal

from .cell import Cell, empty_code_cell
from .environment import BaseEnvironment, PythonEnvironment
from .dependency_analyzer import (
    build_dependency_graph,
    find_cells_to_rerun,
    detect_changed_cells,
)

import logging

logger = logging.getLogger(__name__)


class Processor:
    def __init__(
        self,
        use_dependency_tracking: bool = True,
        environment_type: Literal["python", "ipython"] = "python",
        kernel_timeout: float = 30.0,
    ):
        """Initialize the processor with specified environment type.

        Args:
            use_dependency_tracking: Whether to track cell dependencies
            environment_type: Type of environment to use ("python" or "ipython")
            kernel_timeout: Timeout for IPython kernel operations (seconds)
        """
        self.environment = self._create_environment(environment_type, kernel_timeout)
        self.cells: list[Cell] = []
        self.use_dependency_tracking = use_dependency_tracking
        self.environment_type = environment_type

    def _create_environment(
        self, environment_type: Literal["python", "ipython"], kernel_timeout: float
    ) -> BaseEnvironment:
        """Create the appropriate environment based on type.

        Args:
            environment_type: Type of environment to create
            kernel_timeout: Timeout for IPython kernel operations

        Returns:
            The created environment instance

        Raises:
            ImportError: If ipython is requested but not available
        """
        if environment_type == "ipython":
            try:
                from .ipython_environment import IPythonEnvironment

                env = IPythonEnvironment(timeout=kernel_timeout)
                # Start the kernel immediately
                env.start()
                return env
            except ImportError as e:
                raise ImportError(
                    "IPython environment requires jupyter-client and ipykernel. "
                    "Install with: pip install jupyter-client ipykernel"
                ) from e
        else:
            return PythonEnvironment()

    def __del__(self):
        """Cleanup when processor is destroyed."""
        # Stop IPython kernel if using IPython environment
        if hasattr(self, "environment") and hasattr(self.environment, "stop"):
            self.environment.stop()

    def process_cells(self, cells: list[Cell]) -> list[Cell]:
        if self.use_dependency_tracking:
            return self._process_cells_with_dependencies(cells)
        else:
            return self._process_cells_legacy(cells)

    def _process_cells_legacy(self, cells: list[Cell]) -> list[Cell]:
        """Original processing logic for backwards compatibility."""
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
                    cell.copy_execution(previous_code_cell)
                    output.append(cell)
            else:
                output.append(cell)

        self.cells = output
        return output

    def _process_cells_with_dependencies(self, cells: list[Cell]) -> list[Cell]:
        """New processing logic with dependency tracking."""
        # Build dependency graph for new cells
        build_dependency_graph(cells)

        # Detect which cells have changed
        changed_cell_indices = detect_changed_cells(self.cells, cells)

        if not changed_cell_indices and len(cells) == len(self.cells):
            # No changes detected, copy over previous results
            logger.debug("No changes detected, reusing previous results")
            for i, cell in enumerate(cells):
                if i < len(self.cells) and cell.is_code:
                    cell.copy_execution(self.cells[i])
            self.cells = cells
            return cells

        # Find all cells that need to be rerun
        cells_to_rerun = find_cells_to_rerun(cells, changed_cell_indices)

        logger.info(f"Changed cells: {[i + 1 for i in changed_cell_indices]}")
        logger.info(f"Cells to rerun: {[i + 1 for i in cells_to_rerun]}")

        # Copy over results from unchanged cells
        for i, cell in enumerate(cells):
            if cell.is_code and i not in cells_to_rerun:
                # This cell doesn't need to be rerun, copy previous result
                if i < len(self.cells):
                    cell.copy_execution(self.cells[i])

        # Execute cells that need to be rerun, in dependency order
        cells_to_rerun_sorted = sorted(cells_to_rerun)

        for i in cells_to_rerun_sorted:
            if i < len(cells) and cells[i].is_code:
                logger.info(f"Executing cell {i + 1}")
                self.environment.execute_cell(cells[i])

        self.cells = cells
        return cells
