"""Rich display support for various output types."""

import io
import base64
import sys
from typing import Any, Optional
from contextlib import contextmanager


class DisplayHook:
    """Base class for display hooks."""
    
    def can_display(self, obj: Any) -> bool:
        """Check if this hook can display the given object."""
        return False
    
    def display(self, obj: Any) -> str:
        """Convert the object to HTML representation."""
        return str(obj)


class MatplotlibDisplayHook(DisplayHook):
    """Display hook for matplotlib figures."""
    
    def can_display(self, obj: Any) -> bool:
        """Check if object is a matplotlib figure."""
        return hasattr(obj, '__class__') and 'matplotlib.figure.Figure' in str(obj.__class__)
    
    def display(self, obj: Any) -> str:
        """Convert matplotlib figure to HTML with embedded image."""
        try:
            import matplotlib.pyplot as plt
            
            # Save figure to bytes
            img_buffer = io.BytesIO()
            obj.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
            img_buffer.seek(0)
            
            # Encode as base64
            img_str = base64.b64encode(img_buffer.read()).decode()
            
            # Close the figure to free memory
            plt.close(obj)
            
            return f'<div class="matplotlib-figure"><img src="data:image/png;base64,{img_str}" style="max-width: 100%; height: auto;"></div>'
        except Exception as e:
            return f'<div class="matplotlib-figure error">Error displaying plot: {str(e)}</div>'


class PandasDisplayHook(DisplayHook):
    """Display hook for pandas DataFrames."""
    
    def can_display(self, obj: Any) -> bool:
        """Check if object is a pandas DataFrame."""
        return hasattr(obj, 'to_html') and hasattr(obj, 'index')
    
    def display(self, obj: Any) -> str:
        """Convert pandas DataFrame to HTML."""
        try:
            html = obj.to_html(classes='dataframe', table_id='dataframe', escape=False)
            return f'<div class="pandas-dataframe">{html}</div>'
        except Exception as e:
            return f'<div class="pandas-dataframe error">Error displaying DataFrame: {str(e)}</div>'


class ImageDisplayHook(DisplayHook):
    """Display hook for PIL/Pillow images."""
    
    def can_display(self, obj: Any) -> bool:
        """Check if object is a PIL Image."""
        return hasattr(obj, 'save') and hasattr(obj, 'format')
    
    def display(self, obj: Any) -> str:
        """Convert PIL Image to HTML."""
        try:
            img_buffer = io.BytesIO()
            obj.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            img_str = base64.b64encode(img_buffer.read()).decode()
            return f'<div class="pil-image"><img src="data:image/png;base64,{img_str}" style="max-width: 100%; height: auto;"></div>'
        except Exception as e:
            return f'<div class="pil-image error">Error displaying image: {str(e)}</div>'


class RichDisplayManager:
    """Manager for rich display hooks."""
    
    def __init__(self):
        self.hooks = [
            MatplotlibDisplayHook(),
            PandasDisplayHook(),
            ImageDisplayHook(),
        ]
    
    def display(self, obj: Any) -> str:
        """Display an object using the appropriate hook."""
        for hook in self.hooks:
            if hook.can_display(obj):
                return hook.display(obj)
        
        # Default fallback
        return f'<pre class="result-output">{str(obj)}</pre>'
    
    def add_hook(self, hook: DisplayHook):
        """Add a custom display hook."""
        self.hooks.insert(0, hook)  # Insert at beginning for priority


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


def setup_display_hooks():
    """Set up display hooks for IPython-style rich display."""
    display_manager = RichDisplayManager()
    
    # Try to set up IPython display hooks if available
    try:
        from IPython.display import display
        # If IPython is available, we could integrate with it
        pass
    except ImportError:
        pass
    
    return display_manager