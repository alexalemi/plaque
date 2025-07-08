"""Rich display support using marimo-style method resolution."""

import io
import base64
import html
from typing import Any, Optional, Tuple, Union
from contextlib import contextmanager


def display_as_html(obj: Any) -> str:
    """
    Display an object as HTML using marimo-style method resolution:
    1. Check for _display_() method
    2. Check for _mime_() method
    3. Check for IPython-style _repr_*_() methods
    4. Fall back to repr()
    """

    # 1. Check for _display_() method
    if hasattr(obj, "_display_"):
        try:
            display_result = obj._display_()
            return _render_display_result(display_result)
        except Exception:
            pass

    # 2. Check for _mime_() method
    if hasattr(obj, "_mime_"):
        try:
            mime_type, data = obj._mime_()
            return _render_mime_data(mime_type, data)
        except Exception:
            pass

    # 3. Check for IPython-style _repr_*_() methods
    html_result = _try_ipython_reprs(obj)
    if html_result:
        return html_result

    # 4. Check for built-in types with special handling
    builtin_result = _handle_builtin_types(obj)
    if builtin_result:
        return builtin_result

    # 5. Fall back to repr()
    return f'<pre class="result-output">{html.escape(repr(obj))}</pre>'


def _render_display_result(result: Any) -> str:
    """Render the result of a _display_() method."""
    if isinstance(result, str):
        # If it's already HTML, return as-is
        if result.strip().startswith("<") and result.strip().endswith(">"):
            return result
        # Otherwise escape and wrap in pre
        return f'<pre class="result-output">{html.escape(result)}</pre>'
    else:
        # Recursively try to display the returned object
        return display_as_html(result)


def _render_mime_data(mime_type: str, data: str) -> str:
    """Render data based on MIME type."""
    mime_type = mime_type.lower()

    if mime_type == "text/html":
        return data
    elif mime_type == "text/plain":
        return f'<pre class="result-output">{html.escape(data)}</pre>'
    elif mime_type.startswith("image/"):
        # Assume data is base64 encoded
        return f'<div class="mime-image"><img src="data:{mime_type};base64,{data}" style="max-width: 100%; height: auto;"></div>'
    elif mime_type == "application/json":
        return f'<pre class="json-output">{html.escape(data)}</pre>'
    else:
        # Unknown MIME type, treat as plain text
        return f'<pre class="result-output">{html.escape(data)}</pre>'


def _try_ipython_reprs(obj: Any) -> Optional[str]:
    """Try IPython-style _repr_*_() methods in order of preference."""

    # Try _repr_html_() first
    if hasattr(obj, "_repr_html_"):
        try:
            html_repr = obj._repr_html_()
            if html_repr:
                return html_repr
        except Exception:
            pass

    # Try _repr_svg_()
    if hasattr(obj, "_repr_svg_"):
        try:
            svg_repr = obj._repr_svg_()
            if svg_repr:
                return f'<div class="svg-output">{svg_repr}</div>'
        except Exception:
            pass

    # Try _repr_png_()
    if hasattr(obj, "_repr_png_"):
        try:
            png_data = obj._repr_png_()
            if png_data:
                if isinstance(png_data, bytes):
                    png_b64 = base64.b64encode(png_data).decode()
                else:
                    png_b64 = png_data
                return f'<div class="png-output"><img src="data:image/png;base64,{png_b64}" style="max-width: 100%; height: auto;"></div>'
        except Exception:
            pass

    # Try _repr_jpeg_()
    if hasattr(obj, "_repr_jpeg_"):
        try:
            jpeg_data = obj._repr_jpeg_()
            if jpeg_data:
                if isinstance(jpeg_data, bytes):
                    jpeg_b64 = base64.b64encode(jpeg_data).decode()
                else:
                    jpeg_b64 = jpeg_data
                return f'<div class="jpeg-output"><img src="data:image/jpeg;base64,{jpeg_b64}" style="max-width: 100%; height: auto;"></div>'
        except Exception:
            pass

    # Try _repr_markdown_()
    if hasattr(obj, "_repr_markdown_"):
        try:
            md_repr = obj._repr_markdown_()
            if md_repr:
                # Convert markdown to HTML (basic)
                from .formatter import format_markdown

                return f'<div class="markdown-output">{format_markdown(md_repr)}</div>'
        except Exception:
            pass

    # Try _repr_latex_()
    if hasattr(obj, "_repr_latex_"):
        try:
            latex_repr = obj._repr_latex_()
            if latex_repr:
                return f'<div class="math-block">\\[{latex_repr}\\]</div>'
        except Exception:
            pass

    # Try _repr_json_()
    if hasattr(obj, "_repr_json_"):
        try:
            json_repr = obj._repr_json_()
            if json_repr:
                import json

                json_str = json.dumps(json_repr, indent=2)
                return f'<pre class="json-output">{html.escape(json_str)}</pre>'
        except Exception:
            pass

    return None


def _handle_builtin_types(obj: Any) -> Optional[str]:
    """Handle built-in types that need special display logic."""

    # Handle matplotlib figures
    if hasattr(obj, "__class__") and "matplotlib.figure.Figure" in str(obj.__class__):
        try:
            import matplotlib.pyplot as plt

            # Save figure to bytes
            img_buffer = io.BytesIO()
            obj.savefig(img_buffer, format="png", bbox_inches="tight", dpi=100)
            img_buffer.seek(0)

            # Encode as base64
            img_str = base64.b64encode(img_buffer.read()).decode()

            # Close the figure to free memory
            plt.close(obj)

            return f'<div class="matplotlib-figure"><img src="data:image/png;base64,{img_str}" style="max-width: 100%; height: auto;"></div>'
        except Exception as e:
            return f'<div class="matplotlib-figure error">Error displaying plot: {str(e)}</div>'

    # # Handle pandas DataFrames
    # if hasattr(obj, 'to_html') and hasattr(obj, 'index'):
    #     try:
    #         html_table = obj.to_html(classes='dataframe', table_id='dataframe', escape=False)
    #         return f'<div class="pandas-dataframe">{html_table}</div>'
    #     except Exception as e:
    #         return f'<div class="pandas-dataframe error">Error displaying DataFrame: {str(e)}</div>'
    #
    # # Handle PIL/Pillow images
    # if hasattr(obj, 'save') and hasattr(obj, 'format'):
    #     try:
    #         img_buffer = io.BytesIO()
    #         obj.save(img_buffer, format='PNG')
    #         img_buffer.seek(0)
    #
    #         img_str = base64.b64encode(img_buffer.read()).decode()
    #         return f'<div class="pil-image"><img src="data:image/png;base64,{img_str}" style="max-width: 100%; height: auto;"></div>'
    #     except Exception as e:
    #         return f'<div class="pil-image error">Error displaying image: {str(e)}</div>'

    return None


@contextmanager
def capture_matplotlib_plots():
    """Context manager to capture matplotlib plots."""
    try:
        import matplotlib.pyplot as plt

        # Store original show function
        original_show = plt.show
        captured_figures = []

        def capture_show(*args, **kwargs):
            # Get current figure
            fig = plt.gcf()
            if fig.get_axes():  # Only capture if figure has content
                captured_figures.append(fig)
            # Don't call original show to prevent display

        # Replace show function
        plt.show = capture_show

        yield captured_figures

    except ImportError:
        # matplotlib not available
        yield []
    finally:
        try:
            # Restore original show function
            plt.show = original_show
        except:
            pass
