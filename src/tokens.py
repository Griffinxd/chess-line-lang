"""
Token type definitions for the CLL (Chess Language) lexer.
"""

from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    """All token types recognized by the CLL lexer."""

    # --- Keywords ---
    BD = auto()
    BOARD = auto()
    MV = auto()
    MOVE = auto()
    SQ = auto()
    SQUARE = auto()
    TR = auto()
    TURN = auto()
    CL = auto()
    COLOR = auto()
    PC = auto()
    PIECE = auto()
    EMPTY = auto()
    WHITE = auto()       # white, WHITE
    BLACK = auto()       # black, BLACK
    LINE = auto()
    PRINT = auto()
    EVAL = auto()
    THIS = auto()
    STARTING = auto()
    PREMOVE = auto()

    # --- Literals ---
    MOVE_LITERAL = auto()      # e4, Nf3, Qxd5, cxd5, O-O, O-O-O
    SQUARE_LITERAL = auto()    # A1, D5, E8 (uppercase file)
    PIECE_LITERAL = auto()     # W-king, B-Q, white-rook, BLACK-pawn
    STRING_LITERAL = auto()    # "..."

    # --- Operator ---
    ASSIGN = auto()            # <=

    # --- Separators ---
    DOT = auto()               # .
    DOUBLE_COMMA = auto()      # ,,
    COMMA = auto()             # ,
    LBRACE = auto()            # {
    RBRACE = auto()            # }
    LPAREN = auto()            # (
    RPAREN = auto()            # )

    # --- Special ---
    IDENTIFIER = auto()       # variable / function names
    EOF = auto()


# Keyword string -> TokenType mapping
KEYWORDS = {
    "bd":       TokenType.BD,
    "board":    TokenType.BOARD,
    "mv":       TokenType.MV,
    "move":     TokenType.MOVE,
    "sq":       TokenType.SQ,
    "square":   TokenType.SQUARE,
    "tr":       TokenType.TR,
    "turn":     TokenType.TURN,
    "cl":       TokenType.CL,
    "color":    TokenType.COLOR,
    "pc":       TokenType.PC,
    "piece":    TokenType.PIECE,
    "empty":    TokenType.EMPTY,
    "white":    TokenType.WHITE,
    "black":    TokenType.BLACK,
    "WHITE":    TokenType.WHITE,
    "BLACK":    TokenType.BLACK,
    "line":     TokenType.LINE,
    "print":    TokenType.PRINT,
    "eval":     TokenType.EVAL,
    "this":     TokenType.THIS,
    "starting": TokenType.STARTING,
    "premove":  TokenType.PREMOVE,
}


@dataclass
class Token:
    """A single lexical token."""
    type: TokenType
    lexeme: str
    line: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.lexeme!r}, line={self.line})"
