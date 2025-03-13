import logging
import uuid
import sys
import threading

# Create thread-local storage for request IDs
_request_context = threading.local()

# Create a custom logger
logger = logging.getLogger('codex_api')
logger.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create formatter with timestamps and request_id
formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(request_id)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Custom filter to add request_id to log records
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(_request_context, 'request_id', 'SERVERSTARTUP')
        return True

# Add the filter and formatter to the handler
console_handler.addFilter(RequestIdFilter())
console_handler.setFormatter(formatter)

# Add the handler to our logger
logger.addHandler(console_handler)

# Prevent propagation to avoid duplicate logs
logger.propagate = False

def start_log_request():
    """
    Call this at the beginning of an API endpoint to generate a new request ID.
    Returns the generated UUID so you can use it if needed.
    """
    request_id = str(uuid.uuid4())
    _request_context.request_id = request_id
    logger.info(f"Starting new request")
    return request_id

def set_request_id(request_id):
    """Set a specific request ID"""
    _request_context.request_id = request_id
    return request_id

def get_request_id():
    """Get the current request ID"""
    return getattr(_request_context, 'request_id', None)

# Simple logging functions that use our configured logger
def debug(message):
    logger.debug(message)

def info(message):
    logger.info(message)

def warning(message):
    logger.warning(message)

def error(message):
    logger.error(message)
    
# Log that the logging configuration has been initialized
info("Logging configuration initialized")