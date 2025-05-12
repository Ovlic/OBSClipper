
import logging

log = logging.getLogger("VC_Bot.\u001b[38;5;226;1mutils\u001b[0m")

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors"""

    LEVEL_COLOURS = [
        # (logging.DEBUG, '\x1b[35;1m'),
        # (logging.INFO, '\x1b[36;1m'),
        # (logging.WARNING, '\x1b[33;1m'),
        # (logging.ERROR, '\x1b[31m'),
        # (logging.CRITICAL, '\x1b[41m')
        (logging.DEBUG, '\x1b[38;5;34;1m'),# \u001b[38;5;34;1m
        (logging.INFO, '\x1b[38;5;129;1m'),
        (logging.WARNING, '\x1b[38;5;220;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]

    format = "%(levelname)s - %(message)s"

    FORMATS = {
        level: logging.Formatter(
            f'\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \u001b[38;5;33;1m%(name)s\u001b[0m %(message)s',
            '%Y-%m-%d %H:%M:%S',
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.INFO]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output

def setupLogger():
    logging.root.setLevel(logging.NOTSET)
    handler = logging.StreamHandler()
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = CustomFormatter()
    logger = logging.getLogger("VC_Bot")
    handler.setFormatter(formatter)
    logger.setLevel(logging.NOTSET)
    logger.addHandler(handler)
    
    return logger
