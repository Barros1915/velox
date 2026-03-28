"""
Sistema de Logging do Velox Framework
"""

import logging
import sys
from pathlib import Path

_DEFAULT = 'velox'


class Logger:
    """Sistema de logging do framework"""

    _loggers: dict = {}

    @staticmethod
    def setup(name=_DEFAULT, level='INFO', log_file=None):
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        logger.handlers.clear()

        fmt = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

        if log_file:
            p = Path(log_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setFormatter(fmt)
            logger.addHandler(fh)

        Logger._loggers[name] = logger
        return logger

    @staticmethod
    def get(name=_DEFAULT):
        if name not in Logger._loggers:
            Logger.setup(name)
        return Logger._loggers[name]

    @staticmethod
    def debug(message, name=_DEFAULT):    Logger.get(name).debug(message)

    @staticmethod
    def info(message, name=_DEFAULT):     Logger.get(name).info(message)

    @staticmethod
    def warning(message, name=_DEFAULT):  Logger.get(name).warning(message)

    @staticmethod
    def error(message, name=_DEFAULT):    Logger.get(name).error(message)

    @staticmethod
    def critical(message, name=_DEFAULT): Logger.get(name).critical(message)


class RequestLogger:
    """Logger específico para requisições HTTP"""

    def __init__(self, logger=None):
        self.logger = logger or Logger.get('velox.requests')

    def log_request(self, method, path, status_code, duration_ms):
        self.logger.info(f'{method} {path} {status_code} {duration_ms:.1f}ms')

    def log_error(self, method, path, error):
        self.logger.error(f'{method} {path} ERROR: {error}')


def get_logger(name=None):
    """Retorna um logger Velox"""
    return Logger.get(name or _DEFAULT)
