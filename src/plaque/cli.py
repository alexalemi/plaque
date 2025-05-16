
from .parser import parse, CellType
import logging

import click

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

@click.command()
@click.argument('input', type=click.File('r'))
@click.argument('output', type=click.File('w'))
def render(input, output):
    """Renders the file into its html page."""
    click.echo(type(input))
    logger.info(f"Processing {input.name}")

    for cell in parse(input):
        if cell.type == CellType.MARKDOWN:
            click.secho("MARKDOWN", fg='green')
            click.echo(cell.content.strip())
        elif cell.type == CellType.CODE:
            click.secho("CODE", fg='blue')
            click.echo(cell.content.strip())

    logger.info(f"Outputing to {output.name}")

if __name__ == "__main__":
    render()
