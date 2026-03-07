import logging

from functools import wraps

from types import FunctionType

log = logging.getLogger(__name__)


def exception_handler(func: FunctionType):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.error(e)
            raise e
    return wrapper