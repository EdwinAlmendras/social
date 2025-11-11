"""Config command for CLI - Manage configuration."""
import typer
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

from social.config import Config
from social.logger import logger

app = typer.Typer()
console = Console()


@app.command()
def show(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Show current configuration."""
    try:
        config = Config()
        
        if json_output:
            config_dict = {
                'CONFIG_DIR': str(config.CONFIG_DIR),
                'COOKIES_DIR': str(config.COOKIES_DIR),
                'SESSIONS_DIR': str(config.SESSIONS_DIR),
                'DOWNLOADS_DIR': str(config.DOWNLOADS_DIR),
                'PLATFORMS_FILE': str(config.PLATFORMS_FILE),
                'TELEGRAM_SESSION_FILE': str(config.TELEGRAM_SESSION_FILE),
                'BOT_SESSION_FILE': str(config.BOT_SESSION_FILE),
                'MAX_PARALLEL_DOWNLOADS': config.MAX_PARALLEL_DOWNLOADS,
            }
            console.print(json.dumps(config_dict, indent=2))
        else:
            table = Table(title="Configuration", show_header=True)
            table.add_column("Setting", style="cyan", no_wrap=True)
            table.add_column("Value", style="white")
            table.add_column("Exists/Info", style="green")
            
            settings = [
                ("CONFIG_DIR", config.CONFIG_DIR, "✓" if config.CONFIG_DIR.exists() else "✗"),
                ("COOKIES_DIR", config.COOKIES_DIR, "✓" if config.COOKIES_DIR.exists() else "✗"),
                ("SESSIONS_DIR", config.SESSIONS_DIR, "✓" if config.SESSIONS_DIR.exists() else "✗"),
                ("DOWNLOADS_DIR", config.DOWNLOADS_DIR, "✓" if config.DOWNLOADS_DIR.exists() else "✗"),
                ("PLATFORMS_FILE", config.PLATFORMS_FILE, "✓" if config.PLATFORMS_FILE.exists() else "✗"),
                ("TELEGRAM_SESSION_FILE", config.TELEGRAM_SESSION_FILE, "✓" if config.TELEGRAM_SESSION_FILE.exists() else "✗"),
                ("BOT_SESSION_FILE", config.BOT_SESSION_FILE, "✓" if config.BOT_SESSION_FILE.exists() else "✗"),
                ("MAX_PARALLEL_DOWNLOADS", str(config.MAX_PARALLEL_DOWNLOADS), ""),
            ]
            
            for name, value, info in settings:
                table.add_row(name, str(value), info)
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Config show error: {e}")
        raise typer.Exit(1)


@app.command()
def set_parallel(
    value: int = typer.Argument(..., help="Number of max parallel downloads (1-10)"),
):
    """Set max parallel downloads in .env file."""
    try:
        if value < 1 or value > 10:
            console.print("[red]Error:[/red] Value must be between 1 and 10")
            raise typer.Exit(1)
        
        # Find .env file
        env_file = Path.cwd() / ".config" / ".env"
        if not env_file.exists():
            env_file = Path.cwd() / ".env"
            if not env_file.exists():
                console.print(f"[yellow].env file not found, creating one at: {env_file}[/yellow]")
                env_file.touch()
        
        # Read existing .env content
        env_lines = []
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()
        
        # Update or add MAX_PARALLEL_DOWNLOADS
        updated = False
        for i, line in enumerate(env_lines):
            if line.strip().startswith('MAX_PARALLEL_DOWNLOADS='):
                env_lines[i] = f'MAX_PARALLEL_DOWNLOADS={value}\n'
                updated = True
                break
        
        if not updated:
            env_lines.append(f'MAX_PARALLEL_DOWNLOADS={value}\n')
        
        # Write back to .env
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(env_lines)
        
        console.print(f"[green]✓ MAX_PARALLEL_DOWNLOADS set to {value} in {env_file}[/green]")
        console.print("[yellow]Note: Restart any running processes to apply changes[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Set parallel error: {e}")
        raise typer.Exit(1)


@app.command()
def platforms(
    edit: bool = typer.Option(False, "--edit", "-e", help="Open platforms.json in editor"),
):
    """Show or edit platforms configuration."""
    try:
        config = Config()
        
        if edit:
            import os
            import subprocess
            
            # Create file if it doesn't exist
            if not config.PLATFORMS_FILE.exists():
                config.PLATFORMS_FILE.parent.mkdir(parents=True, exist_ok=True)
                default_config = {
                    "youtube": {
                        "format": "bestvideo+bestaudio/best",
                        "cookies": "youtube.txt",
                        "extra_opts": {
                            "writeinfojson": False
                        }
                    },
                    "vk": {
                        "format": "best",
                        "cookies": "vk.txt"
                    },
                    "rutube": {
                        "format": "best",
                        "cookies": "rutube.txt"
                    }
                }
                with open(config.PLATFORMS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
            
            # Open in default editor
            if os.name == 'nt':  # Windows
                os.startfile(config.PLATFORMS_FILE)
            else:  # Unix-like
                editor = os.environ.get('EDITOR', 'nano')
                subprocess.call([editor, str(config.PLATFORMS_FILE)])
        else:
            platforms_config = config.load_platforms_config()
            
            if not platforms_config:
                console.print("[yellow]No platforms configuration found.[/yellow]")
                console.print(f"Create one at: {config.PLATFORMS_FILE}")
                console.print("\nUse [cyan]--edit[/cyan] to create and edit the configuration.")
            else:
                console.print(f"[cyan]Platforms configuration:[/cyan] {config.PLATFORMS_FILE}\n")
                
                syntax = Syntax(
                    json.dumps(platforms_config, indent=2),
                    "json",
                    theme="monokai",
                    line_numbers=True
                )
                console.print(syntax)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Platforms config error: {e}")
        raise typer.Exit(1)


@app.command()
def cookies(
    platform: str = typer.Argument(..., help="Platform name (youtube, vk, rutube)"),
    path: Path = typer.Option(None, "--path", "-p", help="Path to cookies file to copy"),
    show: bool = typer.Option(False, "--show", "-s", help="Show cookies file path"),
):
    """Manage cookies for platforms."""
    try:
        config = Config()
        
        cookies_file = config.COOKIES_DIR / f"{platform.lower()}.txt"
        
        if show:
            console.print(f"[cyan]Cookies file for {platform}:[/cyan]")
            console.print(f"  Path: {cookies_file}")
            console.print(f"  Exists: {'✓ Yes' if cookies_file.exists() else '✗ No'}")
            
            if cookies_file.exists():
                size = cookies_file.stat().st_size
                console.print(f"  Size: {size} bytes")
        
        elif path:
            if not path.exists():
                console.print(f"[red]Error:[/red] File not found: {path}")
                raise typer.Exit(1)
            
            # Copy cookies file
            import shutil
            config.COOKIES_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy(path, cookies_file)
            
            console.print(f"[green]✓ Cookies copied successfully![/green]")
            console.print(f"  From: {path}")
            console.print(f"  To: {cookies_file}")
        
        else:
            console.print(f"[cyan]Cookies for {platform}:[/cyan]")
            console.print(f"  Expected location: {cookies_file}")
            console.print(f"  Status: {'✓ Found' if cookies_file.exists() else '✗ Not found'}")
            console.print("\nUse [cyan]--path[/cyan] to copy a cookies file to the correct location.")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Cookies management error: {e}")
        raise typer.Exit(1)


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing configuration"),
):
    """Initialize configuration with default values."""
    try:
        config = Config()
        
        # Create directories
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config.COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        config.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create default platforms.json
        if not config.PLATFORMS_FILE.exists() or force:
            default_platforms = {
                "youtube": {
                    "format": "bestvideo+bestaudio/best",
                    "cookies": "youtube.txt",
                    "extra_opts": {
                        "writeinfojson": False
                    }
                },
                "vk": {
                    "format": "best",
                    "cookies": "vk.txt"
                },
                "rutube": {
                    "format": "best",
                    "cookies": "rutube.txt"
                }
            }
            with open(config.PLATFORMS_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_platforms, f, indent=2)
            console.print(f"[green]✓ Created platforms.json[/green]")
        
        console.print("\n[green]✓ Configuration initialized successfully![/green]")
        console.print(f"\nConfiguration directory: {config.CONFIG_DIR}")
        console.print(f"Cookies directory: {config.COOKIES_DIR}")
        console.print(f"Downloads directory: {config.DOWNLOADS_DIR}")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Config init error: {e}")
        raise typer.Exit(1)
