"""loguru logger config that breaks the logger into a console and file
Takes a filename as an input and returns the new logger."""
import io
import sys
from loguru import logger

def setup_logger(logfile):
    logger.remove()  # Remove the default configuration

    logger.add(
        sink=io.TextIOWrapper(sys.stdout.buffer, write_through=True),
        format="<light-black>{time:YYYY-MM-DD HH:mm:ss}</light-black> | <level>{level: <8}</level> | <light-yellow>{message: ^27}</light-yellow> | <light-red>{extra}</light-red>",
        level="INFO",
        colorize=True
    )

    logger.add(
        logfile,
        rotation="20 MB",
        format="<light-black>{time:YYYY-MM-DD HH:mm:ss}</light-black> | <level>{level: <8}</level> | <light-yellow>{message: ^27}</light-yellow> | <light-red>{extra}</light-red>",
        level="INFO",
        colorize=False
    )

    logger.info("\n\n\nMetatron3 STARTUP")

    return logger
