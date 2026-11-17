"""
Created on Feb 6, 2026
@author: keith.chambers

Centralized logging configuration for python.
"""

# For each module add the following 3 lines to the top of the module
#
# #setup logging for this module
# import logging
# logger = logging.getLogger(__name__)

from __future__ import annotations

import logging
from typing import Iterable

#APP_NAMESPACE = "AskMeApp"

NOISY_LIBRARIES: tuple[str, ...] = (
    "kivy",
    "kivy.uix",
    "kivy.core",
    "google",
    "google_genai",
    "google.ai",
    "google.generativeai",
    "httpx",
    "httpcore",
    "grpc",
    "keyring",
)

LOG_FORMAT = "[%(levelname)-7s] [%(name)-22s] %(message)s"

LIB_LOG_LEVEL = logging.WARNING
APP_LOG_LEVEL = logging.INFO


# -----------------------------------------------------------------------------
# Phase 1: Base logging setup (call BEFORE importing frameworks)
# -----------------------------------------------------------------------------
#===============================================================================
# base logging setup
#===============================================================================
def configure_base_logging(
    *,
    level: int = LIB_LOG_LEVEL,
    fmt: str = LOG_FORMAT,
) -> None:
    """ 
    Args:
        level:
        fmt:
    """

    root = logging.getLogger()
    formatter = logging.Formatter(fmt)

    stream_handler_found = False

    for h in root.handlers:
        if isinstance(h, logging.StreamHandler):
            h.setFormatter(formatter)
            stream_handler_found = True

    if not stream_handler_found:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)

    root.setLevel(level)    
    
# -----------------------------------------------------------------------------
# Post-import enforcement (call AFTER Kivy is running)
# -----------------------------------------------------------------------------

def enforce_library_levels(
        app_namespace: str,
    *,
    app_level: int = APP_LOG_LEVEL,
    library_level: int = LIB_LOG_LEVEL,
    libraries: Iterable[str] = NOISY_LIBRARIES,
) -> None:
    """
    Set logging levels for application and external libraries.

    Args:
        app_namespace: Application logger namespace.
        app_level: Logging level for the application.
        library_level: Logging level for external libraries.
        libraries: External library logger names.

    Raises:
        TypeError: If app_namespace is not a string.
        ValueError: If app_namespace is empty.
    """

    # Validate application namespace.
    if not isinstance(app_namespace, str):
        raise TypeError(
            "app_namespace must be a string"
        )

    if not app_namespace.strip():
        raise ValueError(
            "app_namespace cannot be empty"
        )

    
    for name in libraries:
        logging.getLogger(name).setLevel(library_level)

    logging.getLogger(app_namespace).setLevel(app_level)
    
