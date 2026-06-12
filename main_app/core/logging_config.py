import logging
from logging.handlers import RotatingFileHandler

LOG_FORMAT = (
    "%(asctime)s - %(levelname)s - "
    "%(name)s - %(message)s"
)

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT
)

file_handler = RotatingFileHandler(
    "app.log",
    maxBytes=1024 * 1024,
    backupCount=5
)

file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

logger = logging.getLogger("ecommerce")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)