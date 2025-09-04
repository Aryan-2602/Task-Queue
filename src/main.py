"""Main application entry point."""

import asyncio
import signal
import structlog
from src.config import settings
from src.database import create_tables

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def main():
    """Main function."""
    logger.info("Starting Distributed Job Scheduler", version="1.0.0")
    
    # Create database tables
    create_tables()
    
    logger.info("Application initialized successfully")


if __name__ == "__main__":
    main()
