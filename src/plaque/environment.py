"""The main execution environment."""

import ast
import code
from .cell import Cell

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class Environment:
    def __init__(self):
        self.repl = code.InteractiveInterpreter({"__name__": "__main__"})

    def execute_cell(self, cell: Cell):
        assert cell.is_code, "Can only execute code cells."
        logger.debug(f"Asked to execute cell with {cell.content}")
        stmts = list(ast.iter_child_nodes(ast.parse(cell.content)))
        if not stmts:
            return None
        if isinstance(stmts[-1], ast.Expr):
            # the last statement is an expression.
            if len(stmts) > 1:
                self.repl.runcode(compile(ast.Module(body=stmts[:-1]), '<cell>', 'exec'))
            # then eval the last one
            logger.debug(f"Last value: {stmts[-1].value} or {ast.unparse(stmts[-1])}")
            code_obj = self.repl.compile(ast.unparse(stmts[-1]), '<code>', 'single')
            assert code_obj is not None
            result = self.repl.runcode(code_obj)
            logger.debug(f"Got {result=}")
            cell.result = result
            return result
        else:
            code_obj = self.repl.compile(cell.content, "<code>", "exec")
            if code_obj is None:
                cell.error = "Incomplete command!"
                return
            else:
                return self.repl.runcode(code_obj)



