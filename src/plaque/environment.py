"""The main execution environment."""

import ast
import sys
import traceback
from types import CodeType
from typing import Any, Optional
from .cell import Cell
from .display import capture_matplotlib_plots

import builtins


class Environment:
    def __init__(self):
        self.locals = {"__name__": "__main__"}
        self.globals = {}

    def eval(self, source: str | CodeType):
        return builtins.eval(source, self.globals, self.locals)

    def exec(self, source: str | CodeType):
        return builtins.exec(source, self.globals, self.locals)

    def compile(self, source, mode='exec'):
        try:
            return builtins.compile(source, '<cell>', mode)
        except SyntaxError as e:
            return None, str(e)

    def execute_cell(self, cell: Cell):
        """Execute a code cell with proper error handling and rich display."""
        assert cell.is_code, "Can only execute code cells."
        
        # Clear previous results
        cell.result = None
        cell.error = None
        
        try:
            # Parse the cell content
            tree = ast.parse(cell.content)
            stmts = list(ast.iter_child_nodes(tree))
            
            if not stmts:
                return None
            
            # Capture matplotlib plots during execution
            with capture_matplotlib_plots() as captured_figures:
                if isinstance(stmts[-1], ast.Expr):
                    # The last statement is an expression - execute preceding statements
                    if len(stmts) > 1:
                        exec_code = self.compile(ast.Module(body=stmts[:-1], type_ignores=[]), 'exec')
                        if isinstance(exec_code, tuple):  # Error occurred
                            cell.error = exec_code[1]
                            return None
                        self.exec(exec_code)
                    
                    # Evaluate the last expression
                    eval_code = self.compile(ast.unparse(stmts[-1]), 'eval')
                    if isinstance(eval_code, tuple):  # Error occurred
                        cell.error = eval_code[1]
                        return None
                    
                    result = self.eval(eval_code)
                    
                    # Handle matplotlib figures
                    if captured_figures:
                        # Display the captured figures
                        for fig in captured_figures:
                            cell.result = fig
                            break  # For now, just show the first figure
                    else:
                        cell.result = result
                    
                    return result
                else:
                    # All statements are non-expressions, execute them
                    code_obj = self.compile(cell.content, "exec")
                    if isinstance(code_obj, tuple):  # Error occurred
                        cell.error = code_obj[1]
                        return None
                    
                    self.exec(code_obj)
                    
                    # Handle matplotlib figures
                    if captured_figures:
                        # Display the captured figures
                        for fig in captured_figures:
                            cell.result = fig
                            break  # For now, just show the first figure
                    
                    return None
                    
        except Exception as e:
            # Capture runtime errors
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Get traceback but clean it up
            tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
            
            # Filter out internal plaque frames
            filtered_tb = []
            for line in tb_lines:
                if '<cell>' in line or not any(internal in line for internal in ['plaque/', 'environment.py']):
                    filtered_tb.append(line)
            
            if filtered_tb:
                cell.error = ''.join(filtered_tb).strip()
            else:
                cell.error = f"{error_type}: {error_msg}"
            
            return None



