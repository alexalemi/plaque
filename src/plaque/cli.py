from .parser import parse
from .formatter import format
from .environment import Environment
from .server import start_notebook_server
import logging
import sys
import webbrowser
from pathlib import Path

import click

logger = logging.getLogger(__name__)


def process_notebook(input_path: str) -> str:
    """Process a notebook file and return the HTML content."""
    logger.info(f"Processing {input_path}")
    
    with open(input_path, 'r') as f:
        cells = list(parse(f))

    env = Environment()
    for cell in cells:
        if cell.is_code:
            env.execute_cell(cell)

    return format(cells)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def main(verbose):
    """Plaque - A local-first notebook system for Python."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


@main.command()
@click.argument("input", type=click.Path(exists=True, dir_okay=False))
@click.argument("output", type=click.Path(), required=False)
@click.option("--open", "open_browser", is_flag=True, help="Open browser automatically")
def render(input, output, open_browser):
    """
    Render a Python notebook file to static HTML.
    
    INPUT: Path to the Python notebook file
    OUTPUT: Path for the HTML output (optional, defaults to INPUT.html)
    
    Examples:
    
      plaque render my_notebook.py
      plaque render my_notebook.py output.html
    """
    input_path = Path(input).resolve()
    
    if output is None:
        output_path = input_path.with_suffix('.html')
    else:
        output_path = Path(output)
    
    try:
        html_content = process_notebook(str(input_path))
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        click.echo(f"Generated: {output_path}")
        
        if open_browser:
            webbrowser.open(f"file://{output_path.resolve()}")
            
    except Exception as e:
        click.echo(f"Error processing {input_path}: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("input", type=click.Path(exists=True, dir_okay=False))
@click.option("--port", default=5000, help="Port for live server (default: 5000)")
@click.option("--open", "open_browser", is_flag=True, help="Open browser automatically")
def watch(input, port, open_browser):
    """
    Start live server with auto-reload for a Python notebook file.
    
    INPUT: Path to the Python notebook file
    
    Examples:
    
      plaque watch my_notebook.py
      plaque watch my_notebook.py --port 8000
      plaque watch my_notebook.py --open
    """
    input_path = Path(input).resolve()
    
    try:
        start_notebook_server(
            notebook_path=input_path,
            port=port,
            regenerate_callback=process_notebook,
            open_browser=open_browser
        )
    except ImportError as e:
        click.echo(f"Server dependencies not available: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
