import logging.config
import os
def configure_logger():
    """
    Configures the root logger to enable simultaneous logging to console and a log file.

    This configuration is read from an external .ini file. 
    It sets up two handlers, a ConsoleHandler for console logs and a FileHandler for logs written to 'app.log'. 
    The logging level for both handlers is set to INFO.
    """
    logging.config.fileConfig(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..', 'logging_config.ini'), disable_existing_loggers=False)
