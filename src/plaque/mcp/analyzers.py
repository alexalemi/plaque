"""Enhanced analyzers for code quality and dependency tracking."""

import ast
import re
from typing import Dict, List, Any, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from ..processor import Processor
from ..cell import Cell


@dataclass
class CodeIssue:
    """Represents a code quality issue."""

    cell_index: int
    line_number: int
    severity: str  # 'low', 'medium', 'high'
    issue_type: str
    description: str
    suggestion: Optional[str] = None


@dataclass
class DependencyInfo:
    """Represents dependency information for a variable."""

    name: str
    defined_in: List[int]  # Cell indices where defined
    used_in: List[int]  # Cell indices where used
    modified_in: List[int]  # Cell indices where modified
    type_info: Optional[str] = None


class CodeQualityAnalyzer:
    """Analyzes code quality issues in notebook cells."""

    def __init__(self, processor: Processor):
        self.processor = processor

    def analyze_all(self) -> List[CodeIssue]:
        """Analyze all cells for code quality issues."""
        issues = []

        for i, cell in enumerate(self.processor.cells):
            if cell.is_code:
                issues.extend(self._analyze_cell(i, cell))

        return issues

    def _analyze_cell(self, cell_index: int, cell: Cell) -> List[CodeIssue]:
        """Analyze a single cell for code quality issues."""
        issues = []

        # Parse the cell content
        try:
            tree = ast.parse(cell.content)
        except SyntaxError as e:
            issues.append(
                CodeIssue(
                    cell_index=cell_index,
                    line_number=cell.lineno + (e.lineno - 1 if e.lineno else 0),
                    severity="high",
                    issue_type="syntax_error",
                    description=f"Syntax error: {e.msg}",
                    suggestion="Fix the syntax error before running the cell",
                )
            )
            return issues

        # Analyze AST
        issues.extend(self._analyze_ast(cell_index, cell, tree))

        # Analyze text patterns
        issues.extend(self._analyze_text_patterns(cell_index, cell))

        return issues

    def _analyze_ast(
        self, cell_index: int, cell: Cell, tree: ast.AST
    ) -> List[CodeIssue]:
        """Analyze AST for code quality issues."""
        issues = []

        class QualityVisitor(ast.NodeVisitor):
            def __init__(self, analyzer, cell_index, cell):
                self.analyzer = analyzer
                self.cell_index = cell_index
                self.cell = cell
                self.issues = []

            def visit_FunctionDef(self, node):
                # Check function complexity
                if self._count_statements(node) > 20:
                    self.issues.append(
                        CodeIssue(
                            cell_index=self.cell_index,
                            line_number=self.cell.lineno + node.lineno - 1,
                            severity="medium",
                            issue_type="complexity",
                            description=f"Function {node.name} is too complex ({self._count_statements(node)} statements)",
                            suggestion="Consider breaking this function into smaller functions",
                        )
                    )

                # Check for missing docstrings
                if not ast.get_docstring(node):
                    self.issues.append(
                        CodeIssue(
                            cell_index=self.cell_index,
                            line_number=self.cell.lineno + node.lineno - 1,
                            severity="low",
                            issue_type="documentation",
                            description=f"Function {node.name} lacks a docstring",
                            suggestion="Add a docstring to document the function purpose and parameters",
                        )
                    )

                self.generic_visit(node)

            def visit_For(self, node):
                # Check for potential vectorization opportunities
                if isinstance(node.iter, ast.Call):
                    if (
                        hasattr(node.iter.func, "attr")
                        and node.iter.func.attr == "iterrows"
                    ):
                        self.issues.append(
                            CodeIssue(
                                cell_index=self.cell_index,
                                line_number=self.cell.lineno + node.lineno - 1,
                                severity="medium",
                                issue_type="performance",
                                description="Using iterrows() in a loop is inefficient",
                                suggestion="Consider using vectorized operations or .apply() instead",
                            )
                        )

                self.generic_visit(node)

            def visit_Call(self, node):
                # Check for dangerous functions
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["eval", "exec"]:
                        self.issues.append(
                            CodeIssue(
                                cell_index=self.cell_index,
                                line_number=self.cell.lineno + node.lineno - 1,
                                severity="high",
                                issue_type="security",
                                description=f"Use of {node.func.id}() is dangerous",
                                suggestion="Avoid using eval() or exec() with untrusted input",
                            )
                        )

                self.generic_visit(node)

            def visit_Import(self, node):
                # Check for unused imports (basic check)
                for alias in node.names:
                    import_name = alias.asname if alias.asname else alias.name
                    if not self._is_name_used(import_name):
                        self.issues.append(
                            CodeIssue(
                                cell_index=self.cell_index,
                                line_number=self.cell.lineno + node.lineno - 1,
                                severity="low",
                                issue_type="unused_import",
                                description=f"Import {import_name} appears unused",
                                suggestion="Remove unused imports to keep code clean",
                            )
                        )

                self.generic_visit(node)

            def _count_statements(self, node):
                """Count the number of statements in a node."""
                count = 0
                for child in ast.walk(node):
                    if isinstance(child, ast.stmt):
                        count += 1
                return count

            def _is_name_used(self, name):
                """Check if a name is used in the cell content."""
                # Simple text-based check
                pattern = r"\b" + re.escape(name) + r"\b"
                return len(re.findall(pattern, self.cell.content)) > 1

        visitor = QualityVisitor(self, cell_index, cell)
        visitor.visit(tree)
        issues.extend(visitor.issues)

        return issues

    def _analyze_text_patterns(self, cell_index: int, cell: Cell) -> List[CodeIssue]:
        """Analyze text patterns for code quality issues."""
        issues = []
        lines = cell.content.split("\n")

        for i, line in enumerate(lines):
            line_number = cell.lineno + i

            # Check line length
            if len(line) > 100:
                issues.append(
                    CodeIssue(
                        cell_index=cell_index,
                        line_number=line_number,
                        severity="low",
                        issue_type="style",
                        description=f"Line too long ({len(line)} characters)",
                        suggestion="Consider breaking long lines for better readability",
                    )
                )

            # Check for TODO/FIXME comments
            if re.search(r"#.*\b(TODO|FIXME|XXX)\b", line, re.IGNORECASE):
                issues.append(
                    CodeIssue(
                        cell_index=cell_index,
                        line_number=line_number,
                        severity="low",
                        issue_type="todo",
                        description="TODO/FIXME comment found",
                        suggestion="Address the TODO item or remove the comment",
                    )
                )

            # Check for hardcoded credentials
            if re.search(
                r'(password|token|key|secret)\s*=\s*["\'][^"\']+["\']',
                line,
                re.IGNORECASE,
            ):
                issues.append(
                    CodeIssue(
                        cell_index=cell_index,
                        line_number=line_number,
                        severity="high",
                        issue_type="security",
                        description="Potential hardcoded credential found",
                        suggestion="Use environment variables or secure credential storage",
                    )
                )

        return issues


class DependencyTracker:
    """Tracks variable dependencies and relationships."""

    def __init__(self, processor: Processor):
        self.processor = processor
        self.dependencies: Dict[str, DependencyInfo] = {}

    def analyze_dependencies(self) -> Dict[str, DependencyInfo]:
        """Analyze all variable dependencies."""
        self.dependencies = {}

        # Collect all variables
        all_vars = set()
        for cell in self.processor.cells:
            if cell.is_code:
                all_vars.update(cell.provides)
                all_vars.update(cell.requires)

        # Initialize dependency info
        for var in all_vars:
            self.dependencies[var] = DependencyInfo(
                name=var, defined_in=[], used_in=[], modified_in=[]
            )

        # Populate dependency information
        for i, cell in enumerate(self.processor.cells):
            if cell.is_code:
                for var in cell.provides:
                    if var in self.dependencies:
                        self.dependencies[var].defined_in.append(i)

                for var in cell.requires:
                    if var in self.dependencies:
                        self.dependencies[var].used_in.append(i)

                # Check for modifications (heuristic)
                self._analyze_modifications(i, cell)

        return self.dependencies

    def _analyze_modifications(self, cell_index: int, cell: Cell):
        """Analyze if variables are modified in a cell."""
        try:
            tree = ast.parse(cell.content)
        except SyntaxError:
            return

        class ModificationVisitor(ast.NodeVisitor):
            def __init__(self, tracker, cell_index):
                self.tracker = tracker
                self.cell_index = cell_index

            def visit_AugAssign(self, node):
                # Handle +=, -=, *=, etc.
                if isinstance(node.target, ast.Name):
                    var_name = node.target.id
                    if var_name in self.tracker.dependencies:
                        self.tracker.dependencies[var_name].modified_in.append(
                            self.cell_index
                        )

                self.generic_visit(node)

            def visit_Call(self, node):
                # Handle method calls that might modify objects
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        var_name = node.func.value.id
                        method_name = node.func.attr

                        # Methods that typically modify objects
                        modifying_methods = {
                            "append",
                            "extend",
                            "insert",
                            "remove",
                            "pop",
                            "clear",
                            "sort",
                            "reverse",
                            "update",
                            "add",
                        }

                        if method_name in modifying_methods:
                            if var_name in self.tracker.dependencies:
                                self.tracker.dependencies[var_name].modified_in.append(
                                    self.cell_index
                                )

                self.generic_visit(node)

        visitor = ModificationVisitor(self, cell_index)
        visitor.visit(tree)

    def find_circular_dependencies(self) -> List[List[int]]:
        """Find circular dependencies between cells."""
        # Build dependency graph
        graph = defaultdict(set)

        for i, cell in enumerate(self.processor.cells):
            if cell.is_code:
                graph[i].update(cell.depends_on)

        # Find cycles using DFS
        def find_cycles():
            visited = set()
            rec_stack = set()
            cycles = []

            def dfs(node, path):
                if node in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:]
                    cycles.append(cycle)
                    return

                if node in visited:
                    return

                visited.add(node)
                rec_stack.add(node)
                path.append(node)

                for neighbor in graph[node]:
                    dfs(neighbor, path)

                path.pop()
                rec_stack.remove(node)

            for cell_idx in range(len(self.processor.cells)):
                if cell_idx not in visited:
                    dfs(cell_idx, [])

            return cycles

        return find_cycles()

    def find_unused_variables(self) -> List[str]:
        """Find variables that are defined but never used."""
        unused = []

        for var_name, dep_info in self.dependencies.items():
            if dep_info.defined_in and not dep_info.used_in:
                unused.append(var_name)

        return unused

    def find_undefined_variables(self) -> List[str]:
        """Find variables that are used but never defined."""
        undefined = []

        for var_name, dep_info in self.dependencies.items():
            if dep_info.used_in and not dep_info.defined_in:
                undefined.append(var_name)

        return undefined

    def get_dependency_chains(self) -> Dict[str, List[List[int]]]:
        """Get dependency chains for each variable."""
        chains = {}

        for var_name, dep_info in self.dependencies.items():
            var_chains = []

            # Simple chain: definition -> usage
            for def_cell in dep_info.defined_in:
                for use_cell in dep_info.used_in:
                    if def_cell < use_cell:
                        var_chains.append([def_cell, use_cell])

            if var_chains:
                chains[var_name] = var_chains

        return chains


class PerformanceAnalyzer:
    """Analyzes performance characteristics of notebook cells."""

    def __init__(self, processor: Processor):
        self.processor = processor

    def analyze_performance_issues(self) -> List[CodeIssue]:
        """Analyze performance issues in the notebook."""
        issues = []

        for i, cell in enumerate(self.processor.cells):
            if cell.is_code:
                issues.extend(self._analyze_cell_performance(i, cell))

        return issues

    def _analyze_cell_performance(self, cell_index: int, cell: Cell) -> List[CodeIssue]:
        """Analyze performance issues in a single cell."""
        issues = []

        # Check for common performance anti-patterns
        patterns = [
            (
                r"\.iterrows\(\)",
                "Using iterrows() is slow for large DataFrames",
                "Use vectorized operations or .apply()",
            ),
            (
                r"for\s+\w+\s+in\s+range\(len\(",
                "Using range(len()) pattern is inefficient",
                "Use enumerate() or direct iteration",
            ),
            (
                r"\.append\(\)",
                "Using append() in a loop is inefficient",
                "Pre-allocate list or use list comprehension",
            ),
            (
                r"pd\.concat\(\[.*\]\)",
                "Concatenating in a loop is inefficient",
                "Collect data first, then concatenate once",
            ),
            (
                r"\.apply\(lambda",
                "Lambda in apply() can be slow",
                "Consider vectorized operations or named functions",
            ),
        ]

        for pattern, description, suggestion in patterns:
            if re.search(pattern, cell.content):
                issues.append(
                    CodeIssue(
                        cell_index=cell_index,
                        line_number=cell.lineno,
                        severity="medium",
                        issue_type="performance",
                        description=description,
                        suggestion=suggestion,
                    )
                )

        # Check for nested loops
        try:
            tree = ast.parse(cell.content)
            nested_loops = self._find_nested_loops(tree)
            if nested_loops > 2:
                issues.append(
                    CodeIssue(
                        cell_index=cell_index,
                        line_number=cell.lineno,
                        severity="high",
                        issue_type="performance",
                        description=f"Deeply nested loops detected (depth: {nested_loops})",
                        suggestion="Consider algorithmic improvements or vectorization",
                    )
                )
        except SyntaxError:
            pass

        return issues

    def _find_nested_loops(self, tree: ast.AST) -> int:
        """Find the maximum nesting depth of loops."""
        max_depth = 0

        def find_depth(node, current_depth=0):
            nonlocal max_depth

            if isinstance(node, (ast.For, ast.While)):
                current_depth += 1
                max_depth = max(max_depth, current_depth)

            for child in ast.iter_child_nodes(node):
                find_depth(child, current_depth)

        find_depth(tree)
        return max_depth
