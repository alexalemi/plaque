from .parser import parse
from .formatter import format
from .environment import Environment
import logging

import click

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


@click.command()
@click.argument("input", type=click.File("r"))
@click.argument("output", type=click.File("w"))
def render(input, output):
    """Renders the file into its html page."""
    click.echo(type(input))
    logger.info(f"Processing {input.name}")

    cells = list(parse(input))

    for cell in cells:
        if cell.is_markdown:
            click.secho("MARKDOWN", fg="green")
            click.echo(cell.content.strip())
        elif cell.is_code:
            click.secho("CODE", fg="blue")
            click.echo(cell.content.strip())

    logger.info("Executing cells")
    env = Environment()
    for cell in cells:
        if cell.is_code:
            print(env.execute_cell(cell))
            print(f"New cell {cell=}")

    logger.info(f"Outputing to {output.name}")
    output.write(format(cells))



if __name__ == "__main__":
    render()
