from .parser import parse
from .ast_parser import parse_ast
from .formatter import format
from .server import start_notebook_server
from .processor import Processor
import logging
import sys
import time
import webbrowser
from pathlib import Path
from functools import partial
from typing import Optional

import click

logger = logging.getLogger(__name__)


def process_notebook(
    input_path: str | Path,
    processor: Processor,
    image_dir: Optional[Path] = None,
    use_ast_parser: bool = False,
) -> str:
    logger.info(f"Processing {input_path}")

    with open(input_path, "r") as f:
        if use_ast_parser:
            cells = list(parse_ast(f))
        else:
            cells = list(parse(f))

    cells = processor.process_cells(cells)
    return format(cells, image_dir)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option(
    "--use-ast-parser", is_flag=True, help="Use AST-based parser (experimental)"
)
@click.option(
    "--use-dependency-tracking",
    is_flag=True,
    help="Use dependency tracking for smart execution",
)
@click.pass_context
def main(ctx, verbose, use_ast_parser, use_dependency_tracking):
    """Plaque - A local-first notebook system for Python."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Store options in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["use_ast_parser"] = use_ast_parser
    ctx.obj["use_dependency_tracking"] = use_dependency_tracking


@main.command()
@click.argument("input", type=click.Path(exists=True, dir_okay=False))
@click.argument("output", type=click.Path(), required=False)
@click.option("--open", "open_browser", is_flag=True, help="Open browser automatically")
@click.pass_context
def render(ctx, input, output, open_browser):
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
        output_path = input_path.with_suffix(".html")
    else:
        output_path = Path(output)

    try:
        # Get options from context
        use_ast_parser = ctx.obj.get("use_ast_parser", False)
        use_dependency_tracking = ctx.obj.get("use_dependency_tracking", False)

        processor = Processor(use_dependency_tracking=use_dependency_tracking)
        html_content = process_notebook(
            input_path, processor, use_ast_parser=use_ast_parser
        )

        with open(output_path, "w") as f:
            f.write(html_content)

        click.echo(f"Generated: {output_path}")

        if open_browser:
            webbrowser.open(f"file://{output_path.resolve()}")

    except Exception as e:
        click.echo(f"Error processing {input_path}: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("input", type=click.Path(exists=True, dir_okay=False))
@click.argument("output", type=click.Path(), required=False)
@click.option("--open", "open_browser", is_flag=True, help="Open browser automatically")
@click.pass_context
def watch(ctx, input, output, open_browser):
    """
    Watch a Python notebook file and regenerate HTML on changes.

    INPUT: Path to the Python notebook file
    OUTPUT: Path for the HTML output (optional, defaults to INPUT.html)

    Examples:

      plaque watch my_notebook.py
      plaque watch my_notebook.py output.html
      plaque watch my_notebook.py --open
    """
    from .watcher import FileWatcher
    import time

    input_path = Path(input).resolve()

    if output is None:
        output_path = input_path.with_suffix(".html")
    else:
        output_path = Path(output)

    # Get options from context
    use_ast_parser = ctx.obj.get("use_ast_parser", False)
    use_dependency_tracking = ctx.obj.get("use_dependency_tracking", False)

    processor = Processor(use_dependency_tracking=use_dependency_tracking)

    def regenerate_html(file_path):
        """Regenerate HTML when file changes."""
        try:
            html_content = process_notebook(
                input_path, processor, use_ast_parser=use_ast_parser
            )
            with open(output_path, "w") as f:
                f.write(html_content)
            click.echo(f"Regenerated: {output_path}")

            if open_browser:
                webbrowser.open(f"file://{output_path.resolve()}")
        except Exception as e:
            click.echo(f"Error processing {input_path}: {e}", err=True)

    # Initial generation
    regenerate_html(str(input_path))

    # Set up file watcher
    watcher = FileWatcher(str(input_path), regenerate_html)
    watcher.start()

    try:
        click.echo(f"Watching {input_path.name} -> {output_path}")
        click.echo("Press Ctrl+C to stop")

        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\nStopping watcher...")
    finally:
        watcher.stop()


@main.command()
@click.argument("input", type=click.Path(exists=True, dir_okay=False))
@click.option("--port", default=5000, help="Port for live server (default: 5000)")
@click.option(
    "--bind", default="localhost", help="Host/IP to bind to (default: localhost)"
)
@click.option("--open", "open_browser", is_flag=True, help="Open browser automatically")
@click.pass_context
def serve(ctx, input, port, bind, open_browser):
    """
    Start live server with auto-reload for a Python notebook file.

    INPUT: Path to the Python notebook file

    Examples:

      plaque serve my_notebook.py
      plaque serve my_notebook.py --port 8000
      plaque serve my_notebook.py --open
    """
    input_path = Path(input).resolve()

    # Create a single processor instance to maintain state
    processor = Processor()
    # Get options from context
    use_ast_parser = ctx.obj.get("use_ast_parser", False)
    use_dependency_tracking = ctx.obj.get("use_dependency_tracking", False)

    # Create callback that accepts image_dir parameter
    def callback_with_image_dir(
        notebook_path: str, image_dir: Optional[Path] = None
    ) -> str:
        return process_notebook(
            notebook_path, processor, image_dir, use_ast_parser=use_ast_parser
        )

    try:
        start_notebook_server(
            notebook_path=input_path,
            port=port,
            bind=bind,
            regenerate_callback=callback_with_image_dir,
            open_browser=open_browser,
        )
    except ImportError as e:
        click.echo(f"Server dependencies not available: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
