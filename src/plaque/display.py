"""Rich display support using marimo-style method resolution."""

import io
import base64
from typing import Any, Optional, Union
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


Renderable = Union[HTML, Markdown, Text, PNG, JPEG, SVG, Latex, JSON]


def to_renderable(obj: Any, recursion_depth: int = 0) -> Renderable:
    """
    Convert an object to a renderable data class.
    Resolution order:
    1. Check for _display_()
    2. Check for _mime_()
    3. Check for IPython-style _repr_*_()
    4. Handle built-in types (matplotlib, pandas, PIL)
    5. Fall back to repr()
    """
    if recursion_depth > 10:  # Prevent infinite recursion
        return Text(f"Error: Maximum display recursion depth exceeded.")

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
            return HTML(obj._repr_html_())
        except Exception:
            pass
    if hasattr(obj, "_repr_svg_"):
        try:
            return SVG(obj._repr_svg_())
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
            return Markdown(obj._repr_markdown_())
        except Exception:
            pass
    if hasattr(obj, "_repr_latex_"):
        try:
            return Latex(obj._repr_latex_())
        except Exception:
            pass
    if hasattr(obj, "_repr_json_"):
        try:
            return JSON(obj._repr_json_())
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
            plt.close(obj)  # Free memory
            return PNG(img_buffer.getvalue())
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


@contextmanager
def capture_matplotlib_plots():
    """Context manager to capture matplotlib plots."""
    if not matplotlib:
        yield []
        return

    original_show = plt.show
    captured_figures = []

    def capture_show(*args, **kwargs):
        fig = plt.gcf()
        if fig.get_axes():
            captured_figures.append(fig)
        # Don't call original show to prevent display in non-interactive backend

    plt.show = capture_show
    try:
        yield captured_figures
    finally:
        plt.show = original_show
