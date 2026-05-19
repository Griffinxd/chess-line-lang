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


class TypeCheckError(CllError):
    """Raised when the type checker detects a semantic or type compatibility error."""
    pass


# =====================================================================
# Runtime Errors
# =====================================================================

class RuntimeCllError(CllError):
    """Base error for all CLL runtime errors."""
    pass


class InvalidFENError(RuntimeCllError):
    """Raised when a FEN string cannot be parsed into a valid chess position."""
    pass


class IllegalMoveError(RuntimeCllError):
    """Raised when a chess move cannot legally be played on the current board state."""
    pass


class IncompatiblePremoveError(RuntimeCllError):
    """Raised when two premove sequences cannot be interleaved into one legal chess line."""
    pass


class IllegalBoardError(RuntimeCllError):
    """Raised when a board position violates chess legality rules during evaluation."""
    pass


class EmptySquareError(RuntimeCllError):
    """Raised when reading a square that contains no piece."""
    pass


class UninitializedVariableError(RuntimeCllError):
    """Raised when a declared variable is used before receiving a value."""
    pass


class MissingEngineError(RuntimeCllError):
    """Raised when eval() or eval.move() is called without a configured Stockfish engine."""
    pass


class EngineEvaluationError(RuntimeCllError):
    """Raised when the external chess engine fails during evaluation."""
    pass
