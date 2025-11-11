"""Main CLI application using Typer."""
import typer
import logging

from social.cli.commands import download, config, info, upload, database, channel
from social.logger import set_log_level

app = typer.Typer(
    name="social",
    help="Social media downloader CLI - Download videos from YouTube, VK, Rutube and more",
    add_completion=False,
)

# Register subcommands
app.add_typer(download.app, name="download", help="Download videos from URLs or files")
app.add_typer(upload.app, name="upload", help="Process and upload videos to Telegram")
app.add_typer(database.app, name="database", help="Manage video ID database for duplicate detection")
app.add_typer(config.app, name="config", help="Manage configuration and settings")
app.add_typer(info.app, name="info", help="Get information about videos without downloading")
app.add_typer(channel.app, name="channel", help="Get channel information from video or channel URLs")


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress all output except errors"),
    version: bool = typer.Option(False, "--version", help="Show version"),
):
    """Social media downloader CLI."""
    if version:
        typer.echo("social-downloader v0.1.0")
        raise typer.Exit()
    
    # Configurar nivel de logging basado en flags globales
    if quiet:
        set_log_level(logging.ERROR)
    elif verbose:
        set_log_level(logging.DEBUG)
    else:
        set_log_level(logging.INFO)
    
    # Guardar las opciones globales en el contexto para que los subcomandos puedan acceder
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet


if __name__ == "__main__":
    app()
