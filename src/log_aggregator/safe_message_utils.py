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
    except Exception as e:
        # Handle any other unexpected errors
        return f"[Unexpected error getting message: {type(e).__name__}: {e}]"


def safe_extract_args(record: logging.LogRecord) -> tuple:
    """
    Safely extract args from log record.

    Args:
        record: LogRecord instance

    Returns:
        Args tuple or empty tuple if not available
    """
    try:
        args = getattr(record, "args", ())
        return args if args is not None else ()
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


def safe_get_message_for_comparison(record: logging.LogRecord) -> str:
    """
    Get message for pattern comparison purposes.

    This function is optimized for pattern detection and similarity comparison.
    It attempts to normalize the message format for better matching.

    Args:
        record: LogRecord instance

    Returns:
        Normalized message string suitable for comparison
    """
    try:
        # First try to get the formatted message
        message = safe_get_message(record)

        # If we got an error message, try to extract the raw message
        if message.startswith("[Message formatting error"):
            raw_msg = safe_get_raw_message(record)
            args = safe_extract_args(record)

            # For comparison purposes, create a normalized version
            if isinstance(raw_msg, str) and args:
                # Replace format specifiers with placeholders for comparison
                normalized = raw_msg
                for i, arg in enumerate(args):
                    # Replace common format specifiers with generic placeholders
                    normalized = (
                        normalized.replace("%s", "{ARG}", 1).replace("%d", "{ARG}", 1).replace("%f", "{ARG}", 1)
                    )
                return normalized
            return raw_msg

        return message
    except Exception:
        return "Unknown message"


def safe_extract_keywords(record: logging.LogRecord) -> list[str]:
    """
    Safely extract keywords from log record message for error analysis.

    Args:
        record: LogRecord instance

    Returns:
        List of keywords from the message
    """
    try:
        message = safe_get_message(record).lower()
        # Extract meaningful words (length > 2, alphanumeric)
        words = [word for word in message.split() if len(word) > 2 and word.isalnum()]
        return words[:10]  # Limit to first 10 keywords
    except Exception:
        return []


def safe_message_contains(record: logging.LogRecord, search_term: str) -> bool:
    """
    Safely check if message contains a search term.

    Args:
        record: LogRecord instance
        search_term: Term to search for

    Returns:
        True if message contains search term, False otherwise
    """
    try:
        message = safe_get_message(record).lower()
        return search_term.lower() in message
    except Exception:
        return False
