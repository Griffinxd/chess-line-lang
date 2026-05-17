"""
Error classes for the CLL (Chess Language) compiler.
All errors include line number and descriptive message.
"""


class CllError(Exception):
    """Base error for all CLL compilation/runtime errors."""

    def __init__(self, message: str, line: int):
        self.message = message
        self.line = line
        super().__init__(str(self))

    def __str__(self):
        return f"[Line {self.line}] {self.__class__.__name__}: {self.message}"


class LexerError(CllError):
    """Raised when the lexer encounters an illegal character or malformed token."""
    pass


class ParserError(CllError):
    """Raised when the parser encounters an unexpected token or missing syntax."""
    pass
