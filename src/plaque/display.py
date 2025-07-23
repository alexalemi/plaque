"""Rich display support using marimo-style method resolution.

NOTE: This module is primarily for legacy Environment support.
The new IPythonEnvironment uses IPython's built-in display system instead.
"""

import io
import base64
from typing import Any, Optional
from contextlib import contextmanager
from .renderables import (
    HTML,
    JPEG,
    JSON,
    Latex,
    Markdown,
    PNG,
    SVG,
    Text,
)

# Try to import optional dependencies
try:
    import matplotlib.figure
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from PIL import Image
except ImportError:
    Image = None


Renderable = HTML | Markdown | Text | PNG | JPEG | SVG | Latex | JSON


def to_renderable(obj: Any, recursion_depth: int = 0) -> Renderable:
    """
    Convert an object to a renderable data class.

    NOTE: This function is for legacy Environment support only.
    IPythonEnvironment uses IPython's built-in display formatters instead.

    Resolution order:
    1. Check for _display_()
    2. Check for _mime_()
    3. Check for IPython-style _repr_*_()
    4. Handle built-in types (matplotlib, pandas, PIL)
    5. Fall back to repr()
    """
    if recursion_depth > 10:  # Prevent infinite recursion
        return Text("Error: Maximum display recursion depth exceeded.")

    # 1. _display_() method
    if hasattr(obj, "_display_"):
        try:
            display_result = obj._display_()
            # Recursively convert the result
            return to_renderable(display_result, recursion_depth + 1)
        except Exception:
            pass

    # 2. _mime_() method
    if hasattr(obj, "_mime_"):
        try:
            mime_type, data = obj._mime_()
            if mime_type == "text/html":
                return HTML(data)
            elif mime_type == "text/plain":
                return Text(data)
            elif mime_type == "image/png":
                return PNG(base64.b64decode(data))
            elif mime_type == "image/jpeg":
                return JPEG(base64.b64decode(data))
            elif mime_type == "image/svg+xml":
                return SVG(data)
        except Exception:
            pass

    # 3. IPython-style _repr_*_() methods
    ipython_renderable = _try_ipython_reprs(obj)
    if ipython_renderable:
        return ipython_renderable

    # 4. Built-in types
    builtin_renderable = _handle_builtin_types(obj)
    if builtin_renderable:
        return builtin_renderable

    # 5. Fallback to repr()
    return Text(repr(obj))


def _try_ipython_reprs(obj: Any) -> Optional[Renderable]:
    """Try IPython-style _repr_*_() methods in order of preference."""
    if hasattr(obj, "_repr_html_"):
        try:
            html_repr = obj._repr_html_()
            if html_repr:
                return HTML(html_repr)
        except Exception:
            pass
    if hasattr(obj, "_repr_svg_"):
        try:
            svg_repr = obj._repr_svg_()
            if svg_repr:
                return SVG(svg_repr)
        except Exception:
            pass
    if hasattr(obj, "_repr_png_"):
        try:
            data = obj._repr_png_()
            return PNG(base64.b64decode(data) if isinstance(data, str) else data)
        except Exception:
            pass
    if hasattr(obj, "_repr_jpeg_"):
        try:
            data = obj._repr_jpeg_()
            return JPEG(base64.b64decode(data) if isinstance(data, str) else data)
        except Exception:
            pass
    if hasattr(obj, "_repr_markdown_"):
        try:
            md_repr = obj._repr_markdown_()
            if md_repr:
                return Markdown(md_repr)
        except Exception:
            pass
    if hasattr(obj, "_repr_latex_"):
        try:
            latex_repr = obj._repr_latex_()
            if latex_repr:
                return Latex(latex_repr)
        except Exception:
            pass
    if hasattr(obj, "_repr_json_"):
        try:
            json_repr = obj._repr_json_()
            if json_repr:
                return JSON(json_repr)
        except Exception:
            pass
    return None


def _handle_builtin_types(obj: Any) -> Optional[Renderable]:
    """Handle built-in types that need special display logic."""
    # Handle matplotlib figures
    if matplotlib and isinstance(obj, matplotlib.figure.Figure):
        try:
            img_buffer = io.BytesIO()
            obj.savefig(img_buffer, format="png", bbox_inches="tight", dpi=100)
            img_buffer.seek(0)  # Reset buffer position
            png_data = img_buffer.getvalue()
            plt.close(obj)  # Free memory
            return PNG(png_data)
        except Exception as e:
            return Text(f"Error displaying plot: {e}")

    # Handle pandas DataFrames
    if pd and isinstance(obj, pd.DataFrame):
        try:
            html_table = obj.to_html(
                classes="dataframe", table_id="dataframe", escape=False
            )
            return HTML(html_table)
        except Exception as e:
            return Text(f"Error displaying DataFrame: {e}")

    # Handle PIL/Pillow images
    if Image and isinstance(obj, Image.Image):
        try:
            img_buffer = io.BytesIO()
            obj.save(img_buffer, format="PNG")
            return PNG(img_buffer.getvalue())
        except Exception as e:
            return Text(f"Error displaying image: {e}")

    return None


class _FigureCapture:
    """Helper class to capture matplotlib figures during execution."""

    def __init__(self):
        self.figures = []
        self.initial_fig_nums = set()
        self.new_fig_nums = set()

    def add_figure(self, fig):
        """Add a figure to the capture list."""
        self.figures.append(fig)

    def close_figures(self):
        """Close all captured figures and clean up."""
        if matplotlib:
            for fig_num in self.new_fig_nums:
                plt.close(fig_num)


@contextmanager
def capture_matplotlib_plots():
    """Context manager to capture matplotlib plots created during execution.

    NOTE: This is for legacy Environment support only.
    IPythonEnvironment uses IPython's built-in matplotlib integration instead.
    """
    if not matplotlib:
        # Return an empty capture object when matplotlib is not available
        empty_capture = _FigureCapture()
        yield empty_capture
        return

    # Record figure numbers before execution
    initial_fig_nums = set(plt.get_fignums())

    original_show = plt.show
    capture = _FigureCapture()
    capture.initial_fig_nums = initial_fig_nums

    def capture_show(*args, **kwargs):
        fig = plt.gcf()
        if fig.get_axes():
            capture.add_figure(fig)
        # Don't call original show to prevent display in non-interactive backend

    plt.show = capture_show
    try:
        yield capture
    finally:
        # Restore original show function
        plt.show = original_show

        # Find any new figures created during execution
        current_fig_nums = set(plt.get_fignums())
        new_fig_nums = current_fig_nums - initial_fig_nums
        capture.new_fig_nums = new_fig_nums

        # If no figures were captured via plt.show(), check for new figures
        if not capture.figures and new_fig_nums:
            for fig_num in new_fig_nums:
                fig = plt.figure(fig_num)
                if fig.get_axes():  # Only include figures with content
                    capture.add_figure(fig)
                    break  # Only capture the first new figure for now

        # Store the figure numbers for later cleanup
        # Don't close figures here - let the caller handle cleanup after processing
