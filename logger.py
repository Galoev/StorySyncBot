import logging
from pathlib import Path
from datetime import datetime


def get_logger(name=__name__, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    logger_path = get_logger_path(name)
    fh = logging.FileHandler(logger_path)
    fh.setLevel(level)
    format = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh.setFormatter(format)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(format)
    logger.addHandler(ch)

    return logger

def get_logger_path(name=__name__):
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir()
    
    log_filename = generate_log_filename()
    log_path = logs_dir / Path(log_filename)
    
    return log_path

def generate_log_filename(name=__name__):
    current_time = datetime.now()
    time_str = current_time.strftime("%Y-%m-%d_%H:%M:%S")
    log_filename = f"{time_str}_{name}.log"
    return log_filename

if __name__ == "__main__":
    logger = get_logger()
    logger.debug('debug message')
    logger.info('info message')
    logger.warning('warn message')
    logger.error('error message')
    logger.critical('critical message')
