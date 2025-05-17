"""The main execution environment."""

import ast
from types import CodeType
from .cell import Cell

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
        return builtins.compile(source, '<cell>', mode)


    def execute_cell(self, cell: Cell):
        assert cell.is_code, "Can only execute code cells."
        stmts: list = list(ast.iter_child_nodes(ast.parse(cell.content)))
        if not stmts:
            return None
        if isinstance(stmts[-1], ast.Expr):
            # the last statement is an expression.
            if len(stmts) > 1:
                self.exec(self.compile(ast.Module(body=stmts[:-1]), 'exec'))
            # then eval the last one
            code_obj = self.compile(ast.unparse(stmts[-1]), 'eval')
            assert code_obj is not None
            result = self.eval(code_obj)
            cell.result = result
            return result
        else:
            code_obj = self.compile(cell.content, "exec")
            if code_obj is None:
                cell.error = "Incomplete command!"
                return
            else:
                return self.exec(code_obj)



