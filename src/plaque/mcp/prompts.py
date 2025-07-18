"""Prompt provider for MCP server - analysis workflows for agents."""

import json
from typing import Any, Dict, List, Optional
import time

from ..processor import Processor
from ..api_formatter import cell_to_json


class PromptProvider:
    """Provides analysis prompts for common agent workflows."""

    def __init__(self, processor: Processor):
        self.processor = processor

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List all available analysis prompts."""
        return [
            {
                "name": "analyze_notebook",
                "description": "Comprehensive analysis of notebook code quality, structure, and potential issues",
                "arguments": [
                    {
                        "name": "focus",
                        "description": "Focus area for analysis (quality, performance, security, structure)",
                        "required": False,
                    }
                ],
            },
            {
                "name": "debug_errors",
                "description": "Analyze errors in the notebook and provide debugging suggestions",
                "arguments": [
                    {
                        "name": "cell_index",
                        "description": "Specific cell to debug (optional, analyzes all errors if not provided)",
                        "required": False,
                    }
                ],
            },
            {
                "name": "trace_dependencies",
                "description": "Analyze variable dependencies and data flow through the notebook",
                "arguments": [
                    {
                        "name": "variable",
                        "description": "Specific variable to trace (optional, analyzes all if not provided)",
                        "required": False,
                    }
                ],
            },
            {
                "name": "performance_review",
                "description": "Identify performance bottlenecks and optimization opportunities",
                "arguments": [
                    {
                        "name": "include_suggestions",
                        "description": "Include specific optimization suggestions",
                        "required": False,
                    }
                ],
            },
            {
                "name": "security_audit",
                "description": "Analyze notebook for potential security issues and vulnerabilities",
                "arguments": [
                    {
                        "name": "severity",
                        "description": "Minimum severity level to report (low, medium, high)",
                        "required": False,
                    }
                ],
            },
        ]

    async def get_prompt(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific prompt with arguments."""
        if name == "analyze_notebook":
            return await self._analyze_notebook_prompt(arguments)
        elif name == "debug_errors":
            return await self._debug_errors_prompt(arguments)
        elif name == "trace_dependencies":
            return await self._trace_dependencies_prompt(arguments)
        elif name == "performance_review":
            return await self._performance_review_prompt(arguments)
        elif name == "security_audit":
            return await self._security_audit_prompt(arguments)
        else:
            raise ValueError(f"Unknown prompt: {name}")

    async def _analyze_notebook_prompt(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive notebook analysis prompt."""
        focus = arguments.get("focus", "quality")

        # Gather notebook statistics
        stats = {
            "total_cells": len(self.processor.cells),
            "code_cells": sum(1 for cell in self.processor.cells if cell.is_code),
            "markdown_cells": sum(
                1 for cell in self.processor.cells if not cell.is_code
            ),
            "executed_cells": sum(
                1 for cell in self.processor.cells if cell.counter > 0
            ),
            "error_cells": sum(1 for cell in self.processor.cells if cell.error),
            "variables_defined": len(
                set().union(
                    *(cell.provides for cell in self.processor.cells if cell.provides)
                )
            ),
            "imports": [],
        }

        # Extract imports
        for cell in self.processor.cells:
            if cell.is_code and ("import " in cell.content or "from " in cell.content):
                lines = cell.content.split("\n")
                for line in lines:
                    line = line.strip()
                    if line.startswith(("import ", "from ")):
                        stats["imports"].append(line)

        # Get cells with potential issues
        long_cells = [
            i for i, cell in enumerate(self.processor.cells) if len(cell.content) > 500
        ]
        complex_cells = [
            i
            for i, cell in enumerate(self.processor.cells)
            if cell.content.count("\n") > 20
        ]

        prompt_text = f"""# Notebook Analysis Request

Please analyze this Python notebook focusing on **{focus}**. 

## Notebook Statistics
- Total cells: {stats['total_cells']}
- Code cells: {stats['code_cells']}
- Markdown cells: {stats['markdown_cells']}
- Executed cells: {stats['executed_cells']}
- Cells with errors: {stats['error_cells']}
- Variables defined: {stats['variables_defined']}

## Imports Used
{chr(10).join(f"- {imp}" for imp in stats['imports'][:10])}
{f"... and {len(stats['imports']) - 10} more" if len(stats['imports']) > 10 else ""}

## Areas to Focus On
"""

        if focus == "quality":
            prompt_text += """
- Code style and consistency
- Documentation and comments
- Error handling
- Code organization and structure
- Potential bugs or issues
"""
        elif focus == "performance":
            prompt_text += """
- Computational efficiency
- Memory usage
- Vectorization opportunities
- Caching possibilities
- Bottleneck identification
"""
        elif focus == "security":
            prompt_text += """
- Input validation
- File system operations
- Network requests
- Credential handling
- Potential vulnerabilities
"""
        elif focus == "structure":
            prompt_text += """
- Cell organization
- Logical flow
- Code reusability
- Documentation structure
- Dependencies between cells
"""

        if long_cells:
            prompt_text += f"\n## Long Cells (>500 chars)\nCells {long_cells} are particularly long and may benefit from splitting.\n"

        if complex_cells:
            prompt_text += f"\n## Complex Cells (>20 lines)\nCells {complex_cells} are complex and may benefit from refactoring.\n"

        prompt_text += """
## Instructions
1. Review the notebook structure and content
2. Identify specific issues and improvements
3. Provide actionable recommendations
4. Prioritize suggestions by impact
5. Include specific examples where possible

Please provide a comprehensive analysis focusing on the requested area.
"""

        return {
            "description": f"Analyze notebook with focus on {focus}",
            "messages": [
                {"role": "user", "content": {"type": "text", "text": prompt_text}}
            ],
        }

    async def _debug_errors_prompt(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate error debugging prompt."""
        cell_index = arguments.get("cell_index")

        if cell_index is not None:
            # Debug specific cell
            if cell_index < 0 or cell_index >= len(self.processor.cells):
                raise ValueError(f"Cell index out of range: {cell_index}")

            cell = self.processor.cells[cell_index]
            if not cell.error:
                raise ValueError(f"Cell {cell_index} has no error to debug")

            prompt_text = f"""# Debug Cell {cell_index} Error

## Cell Content
```python
{cell.content}
```

## Error Details
- **Error**: {cell.error}
- **Line**: {cell.lineno}
- **Execution Count**: {cell.counter}
- **Standard Error**: {cell.stderr or "None"}

## Context
- **Variables Required**: {', '.join(cell.requires) if cell.requires else 'None'}
- **Variables Provided**: {', '.join(cell.provides) if cell.provides else 'None'}
- **Dependencies**: {', '.join(map(str, cell.depends_on)) if cell.depends_on else 'None'}

Please help debug this error by:
1. Analyzing the error message and type
2. Identifying the root cause
3. Suggesting specific fixes
4. Providing corrected code if possible
5. Explaining how to prevent similar errors
"""
        else:
            # Debug all errors
            error_cells = [
                (i, cell) for i, cell in enumerate(self.processor.cells) if cell.error
            ]

            if not error_cells:
                raise ValueError("No errors found in notebook")

            prompt_text = f"""# Debug All Notebook Errors

Found {len(error_cells)} cells with errors:

"""

            for i, (cell_idx, cell) in enumerate(error_cells):
                prompt_text += f"""## Error {i+1}: Cell {cell_idx}
- **Line**: {cell.lineno}
- **Error**: {cell.error}
- **Code**: `{cell.content[:100]}{'...' if len(cell.content) > 100 else ''}`
- **Required Variables**: {', '.join(cell.requires) if cell.requires else 'None'}

"""

            prompt_text += """
Please help debug these errors by:
1. Analyzing each error message and type
2. Identifying common patterns or root causes
3. Suggesting fixes in priority order
4. Explaining relationships between errors
5. Providing a debugging strategy
"""

        return {
            "description": f"Debug {'specific cell' if cell_index is not None else 'all'} errors",
            "messages": [
                {"role": "user", "content": {"type": "text", "text": prompt_text}}
            ],
        }

    async def _trace_dependencies_prompt(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate dependency tracing prompt."""
        variable = arguments.get("variable")

        # Build dependency graph
        dependencies = {}
        for i, cell in enumerate(self.processor.cells):
            if cell.is_code:
                dependencies[i] = {
                    "provides": list(cell.provides),
                    "requires": list(cell.requires),
                    "depends_on": list(cell.depends_on),
                    "line": cell.lineno,
                    "executed": cell.counter > 0,
                    "error": cell.error is not None,
                }

        if variable:
            # Trace specific variable
            defining_cells = [
                i
                for i, cell in enumerate(self.processor.cells)
                if variable in cell.provides
            ]
            using_cells = [
                i
                for i, cell in enumerate(self.processor.cells)
                if variable in cell.requires
            ]

            prompt_text = f"""# Trace Variable: {variable}

## Variable Definition
"""
            if defining_cells:
                for cell_idx in defining_cells:
                    cell = self.processor.cells[cell_idx]
                    prompt_text += f"- **Cell {cell_idx}** (line {cell.lineno}): `{cell.content[:100]}{'...' if len(cell.content) > 100 else ''}`\n"
            else:
                prompt_text += "- Variable not found in any cell\n"

            prompt_text += f"""
## Variable Usage
"""
            if using_cells:
                for cell_idx in using_cells:
                    cell = self.processor.cells[cell_idx]
                    prompt_text += f"- **Cell {cell_idx}** (line {cell.lineno}): `{cell.content[:100]}{'...' if len(cell.content) > 100 else ''}`\n"
            else:
                prompt_text += "- Variable not used in any cell\n"

            prompt_text += f"""
## Analysis Request
Please analyze the lifecycle of variable `{variable}`:
1. Where and how it's defined
2. How it's used and modified
3. Any potential issues with its usage
4. Suggestions for improvement
"""
        else:
            # Trace all dependencies
            all_variables = set()
            for cell in self.processor.cells:
                all_variables.update(cell.provides)
                all_variables.update(cell.requires)

            prompt_text = f"""# Trace All Dependencies

## Overview
- Total variables: {len(all_variables)}
- Total code cells: {len(dependencies)}
- Variables: {', '.join(sorted(all_variables))}

## Dependency Graph
"""

            for cell_idx, deps in dependencies.items():
                if deps["provides"] or deps["requires"]:
                    status = "✓" if deps["executed"] else "✗" if deps["error"] else "○"
                    prompt_text += (
                        f"- **Cell {cell_idx}** {status} (line {deps['line']})\n"
                    )
                    if deps["provides"]:
                        prompt_text += f"  - Provides: {', '.join(deps['provides'])}\n"
                    if deps["requires"]:
                        prompt_text += f"  - Requires: {', '.join(deps['requires'])}\n"
                    if deps["depends_on"]:
                        prompt_text += f"  - Depends on cells: {', '.join(map(str, deps['depends_on']))}\n"
                    prompt_text += "\n"

            prompt_text += """
## Analysis Request
Please analyze the dependency structure:
1. Identify dependency chains and cycles
2. Find unused or undefined variables
3. Suggest reordering for better flow
4. Identify potential issues or improvements
5. Recommend refactoring opportunities
"""

        return {
            "description": f"Trace {'variable ' + variable if variable else 'all dependencies'}",
            "messages": [
                {"role": "user", "content": {"type": "text", "text": prompt_text}}
            ],
        }

    async def _performance_review_prompt(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate performance review prompt."""
        include_suggestions = arguments.get("include_suggestions", True)

        # Identify potentially slow operations
        slow_patterns = [
            "for.*in.*:",
            "while.*:",
            "\.iterrows()",
            "\.apply(",
            "\.map(",
            "pd\.concat",
            "\.append(",
            "np\.dot",
            "\.sort(",
            "\.groupby",
        ]

        potential_issues = []
        for i, cell in enumerate(self.processor.cells):
            if cell.is_code:
                for pattern in slow_patterns:
                    if pattern in cell.content.lower():
                        potential_issues.append(
                            {
                                "cell": i,
                                "line": cell.lineno,
                                "pattern": pattern,
                                "code": cell.content[:200],
                            }
                        )

        prompt_text = f"""# Performance Review

## Notebook Overview
- Total cells: {len(self.processor.cells)}
- Code cells: {sum(1 for cell in self.processor.cells if cell.is_code)}
- Executed cells: {sum(1 for cell in self.processor.cells if cell.counter > 0)}

## Potential Performance Issues
"""

        if potential_issues:
            for issue in potential_issues[:10]:  # Limit to first 10
                prompt_text += f"""
### Cell {issue['cell']} (line {issue['line']})
- **Pattern**: `{issue['pattern']}`
- **Code**: `{issue['code']}{'...' if len(issue['code']) >= 200 else ''}`
"""
        else:
            prompt_text += "No obvious performance patterns detected.\n"

        prompt_text += """
## Analysis Request
Please review the notebook for performance optimization opportunities:

1. **Computational Efficiency**
   - Identify inefficient loops or operations
   - Suggest vectorization opportunities
   - Find redundant calculations

2. **Memory Usage**
   - Look for memory-intensive operations
   - Suggest memory optimization techniques
   - Identify potential memory leaks

3. **Data Processing**
   - Review pandas/numpy usage patterns
   - Suggest more efficient data structures
   - Identify bottlenecks in data pipelines

4. **Caching & Memoization**
   - Find repeated expensive operations
   - Suggest caching strategies
   - Identify computation reuse opportunities
"""

        if include_suggestions:
            prompt_text += """
5. **Specific Suggestions**
   - Provide code examples for improvements
   - Suggest alternative approaches
   - Recommend performance tools or libraries
"""

        return {
            "description": "Performance review and optimization suggestions",
            "messages": [
                {"role": "user", "content": {"type": "text", "text": prompt_text}}
            ],
        }

    async def _security_audit_prompt(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate security audit prompt."""
        severity = arguments.get("severity", "medium")

        # Security patterns to look for
        security_patterns = {
            "high": [
                "eval(",
                "exec(",
                "input(",
                "raw_input(",
                "open(",
                "subprocess",
                "os.system",
                "os.popen",
            ],
            "medium": [
                "pickle.load",
                "requests.get",
                "urllib",
                "sql",
                "database",
                "password",
                "token",
                "key",
                "secret",
            ],
            "low": ["print(", "logging", "file", "read", "write"],
        }

        # Check for security issues
        issues = []
        for severity_level in ["high", "medium", "low"]:
            if severity_level == "low" and severity in ["medium", "high"]:
                continue
            if severity_level == "medium" and severity == "high":
                continue

            for pattern in security_patterns[severity_level]:
                for i, cell in enumerate(self.processor.cells):
                    if cell.is_code and pattern in cell.content.lower():
                        issues.append(
                            {
                                "cell": i,
                                "line": cell.lineno,
                                "severity": severity_level,
                                "pattern": pattern,
                                "code": cell.content[:200],
                            }
                        )

        prompt_text = f"""# Security Audit (Minimum Severity: {severity})

## Security Scan Results
Found {len(issues)} potential security issues:

"""

        if issues:
            for issue in issues:
                severity_icon = (
                    "🔴"
                    if issue["severity"] == "high"
                    else "🟡"
                    if issue["severity"] == "medium"
                    else "🟢"
                )
                prompt_text += f"""### {severity_icon} {issue['severity'].upper()}: Cell {issue['cell']} (line {issue['line']})
- **Pattern**: `{issue['pattern']}`
- **Code**: `{issue['code']}{'...' if len(issue['code']) >= 200 else ''}`

"""
        else:
            prompt_text += "No security issues found at the specified severity level.\n"

        prompt_text += """
## Security Analysis Request
Please review the notebook for security vulnerabilities:

1. **Code Injection Risks**
   - Look for eval(), exec(), or similar dangerous functions
   - Check for unsanitized user input
   - Identify dynamic code execution

2. **File System Security**
   - Review file operations for path traversal
   - Check for unsafe file permissions
   - Identify sensitive file access

3. **Network Security**
   - Review HTTP requests and API calls
   - Check for insecure connections
   - Identify potential data leakage

4. **Credential Management**
   - Look for hardcoded passwords or tokens
   - Check for insecure credential storage
   - Identify credential exposure risks

5. **Data Security**
   - Review data handling practices
   - Check for sensitive data in outputs
   - Identify potential data exposure

Please provide specific recommendations for each issue found.
"""

        return {
            "description": f"Security audit with {severity} severity minimum",
            "messages": [
                {"role": "user", "content": {"type": "text", "text": prompt_text}}
            ],
        }
