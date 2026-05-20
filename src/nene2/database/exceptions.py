"""Database exceptions."""


class DatabaseConnectionException(Exception):
    """Raised when a database connection cannot be established."""


class DatabaseIntegrityException(Exception):
    """Raised when a database integrity constraint is violated (UNIQUE, FK, CHECK, etc.)."""
