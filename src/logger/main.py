import click
from tabulate import tabulate

from logger.genkey_json import GENKEY_KEYS, create_corpus_json, save_to_json
from logger.helpers import get_stat_from_db
from logger.Logger import DB_NAME, Logger


@click.group()
def cli():
    """CLI tool to log all keypresses for keyboard layout optimization.

    To see help for each command use: key-logger COMMAND --help"""
    pass


@cli.command()
def run():
    """Start the logger. End the logger with by typing `.end` command."""
    logger = Logger()
    logger.start()
    print("Listening to all keystrokes...")
    while True:
        command = input("Command: ")
        if command == ".end":
            logger.stop()
            break


@cli.command()
@click.argument("ngrams_name", type=str)
@click.option("--limit", "-l", default=20, help="Number of top ngrams to view.")
@click.option("--sort_by", "-s", default="value", help="Sort results by name or value")
def view(ngrams_name, limit, sort_by):
    """View the stats of the logged keys.

    Valid stat names are 'letters', 'bigrams', 'trigrams', 'skipgrams'."""
    if ngrams_name not in GENKEY_KEYS:
        raise click.ClickException(
            f"Invalid argument. Valid arguments are {GENKEY_KEYS}."
        )

    stat = get_stat_from_db(ngrams_name, limit, sort_by, DB_NAME)
    click.echo(tabulate(stat, headers="firstrow", tablefmt="rounded_outline"))


@cli.command()
# @click.option("-f", "--format", default="g", help="Format for consuming analyzers")
def save():
    """Save logged keys to corpus json, default in genkey corput format."""
    # Support genkey only for now so "g" is the only option
    # Use enum for other analyzers later
    data = create_corpus_json(DB_NAME)
    save_to_json(data)


if __name__ == "__main__":
    run()
