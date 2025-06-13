"""Safe message utilities for log aggregation."""

import logging


def safe_get_message(record: logging.LogRecord) -> str:
    """
    Safely get message from log record, handling formatting errors.

    Args:
        record: LogRecord instance

    Returns:
        Formatted message string or error message if formatting fails
    """
    try:
        return record.getMessage()
    except (TypeError, ValueError) as e:
        # Handle string formatting errors
        try:
            # Try to get the raw message without formatting
            msg = getattr(record, "msg", "Unknown message")
            args = getattr(record, "args", ())

            # If msg is a string and has % placeholders, but args don't match
            if isinstance(msg, str) and "%" in msg and args:
                # Try to escape % signs that aren't format specifiers
                safe_msg = msg.replace("%", "%%")
                # Try basic formatting first
                try:
                    return safe_msg % args
                except (TypeError, ValueError):
                    # If that fails, just return the message with args appended
                    return f"{msg} (args: {args})"
            elif isinstance(msg, str):
                return msg
            else:
                return str(msg)
        except Exception:
            # Last resort: return a safe error message
            return f"[Message formatting error: {type(e).__name__}: {e}]"


def safe_extract_args(record: logging.LogRecord) -> tuple:
    """
    Safely extract args from log record.

    Args:
        record: LogRecord instance

    Returns:
        Args tuple or empty tuple if not available
    """
    try:
        return getattr(record, "args", ())
    except Exception:
        return ()


def safe_get_raw_message(record: logging.LogRecord) -> str:
    """
    Get raw message without formatting from log record.

    Args:
        record: LogRecord instance

    Returns:
        Raw message string
    """
    try:
        msg = getattr(record, "msg", "Unknown message")
        return str(msg) if msg is not None else "Unknown message"
    except Exception:
        return "Unknown message"
