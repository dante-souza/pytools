from functools import wraps
from typing import Callable, Optional, Dict, Any, Union
import logging
import traceback
import sys


class Logger:
    """
    A class to handle logging with different levels and formats using loguru.

    Attributes:
        stage (str): The current stage of logging (dev or prod).
    """
    COLOR_RESET = "\033[0m"
    COLOR_INFO = "\033[92m"  # Green
    COLOR_WARNING = "\033[93m"  # Yellow
    COLOR_ERROR = "\033[91m"  # Red
    COLOR_EXTRA = "\033[94m"  # Blue

    logger_format_extras = {
        "INFO": f"{COLOR_INFO}{{asctime}} | {{levelname:<8}} | {{message}} | \nextra info: {COLOR_EXTRA}{{custom_dimensions}}{COLOR_RESET}",
        "WARNING": f"{COLOR_WARNING}{{asctime}} | {{levelname:<8}} | {{message}} | \nextra info: {COLOR_EXTRA}{{custom_dimensions}}{COLOR_RESET}",
        "ERROR": f"{COLOR_ERROR}{{asctime}} | {{levelname:<8}} | {{message}} | \nextra info: {COLOR_EXTRA}{{custom_dimensions}}{COLOR_RESET}",
    }

    logger_format = {
        "INFO": f"{COLOR_INFO}{{asctime}} | {{levelname:<8}} | {{message}}{COLOR_RESET}",
        "WARNING": f"{COLOR_WARNING}{{asctime}} | {{levelname:<8}} | {{message}}{COLOR_RESET}",
        "ERROR": f"{COLOR_ERROR}{{asctime}} | {{levelname:<8}} | {{message}}{COLOR_RESET}",
    }

    def __init__(self, stage: str = "dev"):
        self.stage = stage
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.clear_logger()

    def clear_logger(self):
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

    def _configure_stage(self, extra: Dict[str, Any]):
        if "stage" not in extra:
            return

        stage = extra.get("stage", "prod").lower()

        if stage in ("prod", "production") and self.stage != "prod":
            self.stage = "prod"
        elif stage in ("dev", "development", "test", "testing", "staging", "stage") and self.stage != "dev":
            self.stage = "dev"

    def _configure_extras(self, extra) -> Dict:
        self._configure_stage(extra)
        return {"custom_dimensions": extra}

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self.clear_logger()
        handler = logging.StreamHandler(sys.stdout)
        if extra not in [{}, None]:
            formatter = logging.Formatter(
                self.logger_format_extras["WARNING"], style='{', datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            properties = self._configure_extras(extra)
            self.logger.warning(message, extra=properties)
        else:
            formatter = logging.Formatter(
                self.logger_format["WARNING"], style='{', datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.warning(message)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self.clear_logger()
        handler = logging.StreamHandler(sys.stdout)
        if extra not in [{}, None]:
            formatter = logging.Formatter(
                self.logger_format_extras["INFO"], style='{', datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            properties = self._configure_extras(extra)
            self.logger.info(message, extra=properties)
        else:
            formatter = logging.Formatter(
                self.logger_format["INFO"], style='{', datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.info(message)

    def error(
            self, message: Union[str, Exception], extra: Optional[Dict[str, Any]] = None
    ) -> None:
        self.clear_logger()
        if isinstance(message, Exception):
            message = str(message)
        handler = logging.StreamHandler(sys.stderr)
        if extra not in [{}, None]:
            formatter = logging.Formatter(
                self.logger_format_extras["ERROR"], style='{', datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            properties = self._configure_extras(extra)
            self.logger.error(message, extra=properties, exc_info=True)
        else:
            formatter = logging.Formatter(
                self.logger_format["ERROR"], style='{', datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.error(message, exc_info=True)


def log_with_logger(logger_instance, log_level, message, extra=None):
    logger_instance.clear_logger()
    handler = logging.StreamHandler(sys.stdout)
    if extra not in [{}, None]:
        formatter = logging.Formatter(
            logger_instance.logger_format_extras[log_level], style='{', datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger_instance.logger.addHandler(handler)
        properties = logger_instance._configure_extras(extra)
        getattr(logger_instance.logger, log_level.lower())(message, extra=properties)
    else:
        formatter = logging.Formatter(
            logger_instance.logger_format[log_level], style='{', datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger_instance.logger.addHandler(handler)
        getattr(logger_instance.logger, log_level.lower())(message)


def logger_decorator(log_level: str, extra: Optional[Dict[str, Any]] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger_instance = Logger()
            try:
                log_with_logger(logger_instance, log_level, f"Calling {func.__name__}", extra)
                result = func(*args, **kwargs)
            except Exception as excpt:
                exception_data = {
                    type(excpt).__name__: str(excpt),
                    "traceback": traceback.format_exc(),
                }
                log_with_logger(logger_instance, "ERROR", f"{func.__name__} failed", exception_data)
                raise excpt
            else:
                return result

        return wrapper

    return decorator


if __name__ == '__main__':
    logger = Logger()

    logger.info(f"My func is executing.")
    logger.warning(f"My func is burning.")
    logger.error(f"My func is caput.")

    @logger_decorator(log_level="INFO", extra={"stage": "prod"})
    def example_function():
        print("Inside the decorated function")


    @logger_decorator(log_level="INFO", extra={"stage": "prod"})
    def failed_function():
        return 1 / 0

    example_function()

    failed_function()
