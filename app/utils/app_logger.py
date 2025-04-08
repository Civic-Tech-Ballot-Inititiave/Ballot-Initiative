import structlog
import logging

# Configure the default logging level
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO)
)

logger = structlog.get_logger()

def enable_debug_logging(enable_debugging: bool):
    if enable_debugging:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG) 
        )


    global logger
    logger = structlog.get_logger()