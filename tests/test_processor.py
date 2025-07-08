"""Tests for the processor module."""

import pytest
from unittest.mock import Mock, patch

from src.plaque.processor import Processor
from src.plaque.cell import Cell, CellType


class TestProcessorBasics:
    """Test basic processor functionality."""

    def test_processor_initialization(self):
        """Test processor initializes correctly."""
        processor = Processor()
        assert processor.environment is not None
        assert processor.cells == []

    def test_empty_cell_list(self):
        """Test processing empty cell list."""
        processor = Processor()
        result = processor.process_cells([])
        assert result == []
        assert processor.cells == []

    def test_single_markdown_cell(self):
        """Test processing single markdown cell."""
        processor = Processor()
        cell = Cell(CellType.MARKDOWN, "# Hello", 1)
        
        result = processor.process_cells([cell])
        
        assert result == [cell]
        assert processor.cells == [cell]

    def test_single_code_cell_execution(self):
        """Test processing single code cell executes it."""
        processor = Processor()
        cell = Cell(CellType.CODE, "2 + 3", 1)
        
        result = processor.process_cells([cell])
        
        assert len(result) == 1
        assert result[0].result == 5
        assert result[0].error is None
        assert processor.cells == result


class TestRerunLogic:
    """Test the core rerun logic."""

    def test_unchanged_code_reuses_result(self):
        """Test that unchanged code cells reuse previous results."""
        processor = Processor()
        
        # First run with a code cell
        cell1 = Cell(CellType.CODE, "x = 42", 1)
        result1 = processor.process_cells([cell1])
        
        # Simulate some execution result
        result1[0].result = None
        result1[0].counter = 1
        
        # Second run with same cell content
        cell2 = Cell(CellType.CODE, "x = 42", 1)
        result2 = processor.process_cells([cell2])
        
        # Should reuse the previous result
        assert result2[0].result is None
        assert result2[0].counter == 1
        assert result2[0].error is None

    def test_changed_code_triggers_execution(self):
        """Test that changed code triggers re-execution."""
        processor = Processor()
        
        # First run
        cell1 = Cell(CellType.CODE, "x = 42", 1)
        result1 = processor.process_cells([cell1])
        first_counter = result1[0].counter
        
        # Second run with different content
        cell2 = Cell(CellType.CODE, "x = 100", 1)
        result2 = processor.process_cells([cell2])
        
        # Should execute the new code (counter should advance)
        assert result2[0].counter > first_counter

    def test_off_script_execution(self):
        """Test that once off script, all subsequent cells execute."""
        processor = Processor()
        
        # First run with multiple cells
        cells1 = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "y = 2", 2),
            Cell(CellType.CODE, "z = 3", 3)
        ]
        result1 = processor.process_cells(cells1)
        
        # Set up counters to track execution
        for i, cell in enumerate(result1):
            cell.counter = i + 1
        
        # Second run with change in middle cell
        cells2 = [
            Cell(CellType.CODE, "x = 1", 1),      # Same - should reuse
            Cell(CellType.CODE, "y = 20", 2),     # Different - should execute
            Cell(CellType.CODE, "z = 3", 3)       # Same content but should execute (off script)
        ]
        result2 = processor.process_cells(cells2)
        
        # First cell should reuse result
        assert result2[0].counter == 1
        
        # Second and third cells should execute (off script)
        assert result2[1].counter > 1
        assert result2[2].counter > 1

    def test_markdown_cells_dont_affect_script(self):
        """Test that markdown cells don't affect the off-script logic."""
        processor = Processor()
        
        # First run
        cells1 = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.MARKDOWN, "# Documentation", 2),
            Cell(CellType.CODE, "y = 2", 3)
        ]
        result1 = processor.process_cells(cells1)
        result1[0].counter = 1
        result1[2].counter = 1
        
        # Second run with same content
        cells2 = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.MARKDOWN, "# Documentation", 2),
            Cell(CellType.CODE, "y = 2", 3)
        ]
        result2 = processor.process_cells(cells2)
        
        # Both code cells should reuse results
        assert result2[0].counter == 1
        assert result2[2].counter == 1

    def test_mixed_content_rerun(self):
        """Test rerun logic with mixed markdown and code cells."""
        processor = Processor()
        
        # First run
        cells1 = [
            Cell(CellType.MARKDOWN, "# Title", 1),
            Cell(CellType.CODE, "x = 10", 2),
            Cell(CellType.MARKDOWN, "## Subtitle", 3),
            Cell(CellType.CODE, "y = x * 2", 4)
        ]
        result1 = processor.process_cells(cells1)
        result1[1].counter = 1
        result1[3].counter = 1
        
        # Second run with change in first code cell
        cells2 = [
            Cell(CellType.MARKDOWN, "# Title", 1),
            Cell(CellType.CODE, "x = 20", 2),  # Changed
            Cell(CellType.MARKDOWN, "## Subtitle", 3),
            Cell(CellType.CODE, "y = x * 2", 4)  # Same but off script
        ]
        result2 = processor.process_cells(cells2)
        
        # First code cell should execute (changed)
        assert result2[1].counter > 1
        # Second code cell should execute (off script)
        assert result2[3].counter > 1

    def test_error_handling_in_rerun(self):
        """Test that errors are properly handled during rerun."""
        processor = Processor()
        
        # First run with error
        cell1 = Cell(CellType.CODE, "1 / 0", 1)
        result1 = processor.process_cells([cell1])
        
        # Should have error
        assert result1[0].error is not None
        assert "ZeroDivisionError" in result1[0].error
        
        # Second run with same cell
        cell2 = Cell(CellType.CODE, "1 / 0", 1)
        result2 = processor.process_cells([cell2])
        
        # Should reuse the error
        assert result2[0].error is not None
        assert "ZeroDivisionError" in result2[0].error

    def test_copy_execution_details(self):
        """Test that execution details are properly copied."""
        processor = Processor()
        
        # First run
        cell1 = Cell(CellType.CODE, "42", 1)
        result1 = processor.process_cells([cell1])
        
        # Set up execution details
        result1[0].result = 42
        result1[0].error = None
        result1[0].counter = 5
        
        # Second run with same content
        cell2 = Cell(CellType.CODE, "42", 1)
        result2 = processor.process_cells([cell2])
        
        # Should copy all execution details
        assert result2[0].result == 42
        assert result2[0].error is None
        assert result2[0].counter == 5

    def test_fewer_cells_in_second_run(self):
        """Test handling when second run has fewer cells."""
        processor = Processor()
        
        # First run with multiple cells
        cells1 = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "y = 2", 2),
            Cell(CellType.CODE, "z = 3", 3)
        ]
        result1 = processor.process_cells(cells1)
        
        # Second run with fewer cells
        cells2 = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "y = 2", 2)
        ]
        result2 = processor.process_cells(cells2)
        
        # Should process only the cells provided
        assert len(result2) == 2
        assert processor.cells == result2

    def test_more_cells_in_second_run(self):
        """Test handling when second run has more cells."""
        processor = Processor()
        
        # First run with few cells
        cells1 = [
            Cell(CellType.CODE, "x = 1", 1)
        ]
        result1 = processor.process_cells(cells1)
        result1[0].counter = 1
        
        # Second run with more cells
        cells2 = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "y = 2", 2)
        ]
        result2 = processor.process_cells(cells2)
        
        # First cell should reuse result
        assert result2[0].counter == 1
        # Second cell should execute
        assert result2[1].counter > 0

    def test_empty_code_cell_handling(self):
        """Test that empty code cells are handled properly."""
        processor = Processor()
        
        # First run with empty cell
        cell1 = Cell(CellType.CODE, "", 1)
        result1 = processor.process_cells([cell1])
        
        # Second run with same empty cell
        cell2 = Cell(CellType.CODE, "", 1)
        result2 = processor.process_cells([cell2])
        
        # Should reuse the empty result
        assert result2[0].result is None
        assert result2[0].error is None


class TestProcessorState:
    """Test processor state management."""

    def test_processor_maintains_environment_state(self):
        """Test that processor maintains environment state between runs."""
        processor = Processor()
        
        # First run: define variable
        cell1 = Cell(CellType.CODE, "x = 100", 1)
        processor.process_cells([cell1])
        
        # Second run: use variable
        cell2 = Cell(CellType.CODE, "x + 50", 1)
        result2 = processor.process_cells([cell2])
        
        # Should use the variable from previous run
        assert result2[0].result == 150

    def test_processor_updates_cells_list(self):
        """Test that processor updates its cells list correctly."""
        processor = Processor()
        
        # First run
        cells1 = [Cell(CellType.CODE, "x = 1", 1)]
        result1 = processor.process_cells(cells1)
        assert processor.cells == result1
        
        # Second run with different cells
        cells2 = [Cell(CellType.CODE, "y = 2", 1)]
        result2 = processor.process_cells(cells2)
        assert processor.cells == result2
        assert processor.cells != result1

    @patch('src.plaque.processor.Environment')
    def test_processor_uses_single_environment(self, mock_env_class):
        """Test that processor uses a single environment instance."""
        mock_env = Mock()
        mock_env_class.return_value = mock_env
        
        processor = Processor()
        
        # Process cells multiple times
        cell1 = Cell(CellType.CODE, "x = 1", 1)
        processor.process_cells([cell1])
        
        cell2 = Cell(CellType.CODE, "y = 2", 1)
        processor.process_cells([cell2])
        
        # Environment should be created only once
        mock_env_class.assert_called_once()
        
        # execute_cell should be called for each new/changed cell
        assert mock_env.execute_cell.call_count >= 1