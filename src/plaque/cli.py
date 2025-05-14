
from .parser import parse
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
        click.secho("CELL", fg='red')
        click.echo(cell)

    logger.info(f"Outputing to {output.name}")

if __name__ == "__main__":
    render()

