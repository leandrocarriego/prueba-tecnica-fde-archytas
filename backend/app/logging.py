"""
Logging configuration using Rich for beautiful terminal output.
"""

import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

from app.config import settings

# Local variables in a traceback are a debugging aid in development and a
# credential leak in production: they would print the portal's password and the
# secret key straight into the log. AGENTS.md forbids that, so this is tied to
# the environment rather than left on.
SHOW_LOCALS = settings.is_development

install_rich_traceback(show_locals=SHOW_LOCALS)

# Create console for rich output
console = Console()


def setup_logging() -> None:
    """
    Configure logging with Rich for beautiful terminal output.

    This sets up:
    - Rich handler with colored output
    - Proper log levels based on environment
    - Formatted output with timestamps and module names
    """
    # Determine log level based on environment
    if settings.ENVIRONMENT == "DEVELOPMENT":
        log_level = logging.DEBUG
    elif settings.ENVIRONMENT == "PRODUCTION":
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_path=True,
                tracebacks_show_locals=SHOW_LOCALS,
                markup=True,
            )
        ],
    )

    # Set specific loggers to appropriate levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)

    # Get root logger and log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"[bold green]✓[/bold green] Logging configured for [bold]{settings.ENVIRONMENT}[/bold] environment"
    )
    logger.debug(f"Log level set to: {logging.getLevelName(log_level)}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
