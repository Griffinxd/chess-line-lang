"""
Lexer (lexical analyzer) for the CLL (Chess Language).

Scans source text character-by-character and produces a list of Token objects.
Handles all ambiguity hotspots: castling notation, piece literals vs keywords,
move literals vs identifiers, and square literals.
"""

from tokens import TokenType, Token, KEYWORDS
from errors import LexerError


# --- Piece-literal component sets ---
PIECE_PREFIXES = {"white", "black", "WHITE", "BLACK", "W", "B"}
PIECE_NAMES = {
    "king", "queen", "rook", "bishop", "knight", "pawn",
    "K", "Q", "R", "B", "N", "P",
}

# Characters that are valid in chess piece designators for moves
PIECE_LETTERS = set("KQRBN")


class Lexer:
    """
    Hand-written lexer for CLL source code.

    Usage:
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
    """

    def __init__(self, source: str):
        self.source = source
        self.pos = 0          # current index into source
        self.line = 1         # current line number (1-based)
        self.tokens: list[Token] = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _at_end(self) -> bool:
        return self.pos >= len(self.source)

    def _peek(self, offset: int = 0) -> str:
        """Return char at current pos + offset, or '\\0' if past end."""
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return "\0"

    def _advance(self) -> str:
        """Consume and return the current character."""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
        return ch

    def _add_token(self, token_type: TokenType, lexeme: str, line: int):
        self.tokens.append(Token(token_type, lexeme, line))

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        """Scan the entire source and return a list of tokens."""
        while not self._at_end():
            self._scan_token()
        self._add_token(TokenType.EOF, "", self.line)
        return self.tokens

    # ------------------------------------------------------------------
    # Token scanner
    # ------------------------------------------------------------------

    def _scan_token(self):
        ch = self._peek()

        # 1. Whitespace
        if ch in " \t\r\n":
            self._advance()
            return

        # 2. Comments: // to end of line
        if ch == "/" and self._peek(1) == "/":
            while not self._at_end() and self._peek() != "\n":
                self._advance()
            return

        # 3. String literal: "..."
        if ch == '"':
            self._read_string()
            return

        # 4. Two-char tokens
        if ch == "<" and self._peek(1) == "=":
            line = self.line
            self._advance()  # <
            self._advance()  # =
            self._add_token(TokenType.ASSIGN, "<=", line)
            return

        if ch == "," and self._peek(1) == ",":
            line = self.line
            self._advance()  # ,
            self._advance()  # ,
            self._add_token(TokenType.DOUBLE_COMMA, ",,", line)
            return

        # 5. Single-char separators
        single_char_tokens = {
            ".": TokenType.DOT,
            ",": TokenType.COMMA,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
        }
        if ch in single_char_tokens:
            line = self.line
            self._advance()
            self._add_token(single_char_tokens[ch], ch, line)
            return

        # 6. Word token (letter or underscore)
        if ch.isalpha() or ch == "_":
            self._read_word()
            return

        # 7. Anything else is an error
        line = self.line
        self._advance()
        raise LexerError(f"Unexpected character '{ch}'", line)

    # ------------------------------------------------------------------
    # String literal
    # ------------------------------------------------------------------

    def _read_string(self):
        """Read a string literal: "..." with backslash escapes."""
        line = self.line
        self._advance()  # consume opening "
        value = []

        while not self._at_end() and self._peek() != '"':
            if self._peek() == "\\":
                self._advance()  # consume backslash
                if self._at_end():
                    raise LexerError("Unterminated string literal", line)
                value.append(self._advance())  # consume escaped char
            else:
                value.append(self._advance())

        if self._at_end():
            raise LexerError("Unterminated string literal", line)

        self._advance()  # consume closing "
        full_lexeme = '"' + "".join(value) + '"'
        self._add_token(TokenType.STRING_LITERAL, full_lexeme, line)

    # ------------------------------------------------------------------
    # Word token — the complex part
    # ------------------------------------------------------------------

    def _read_word(self):
        """
        Read an alphanumeric word and classify it as one of:
        PIECE_LITERAL, MOVE_LITERAL (castling), keyword, SQUARE_LITERAL,
        MOVE_LITERAL (standard chess notation), or IDENTIFIER.
        """
        start = self.pos
        line = self.line

        # Read base word: [a-zA-Z_][a-zA-Z0-9_]*
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()

        base_word = self.source[start:self.pos]

        # --- Case 1: Castling (O-O-O or O-O) ---
        if base_word == "O" and self._peek() == "-":
            castling = self._try_castling(start)
            if castling is not None:
                self._add_token(TokenType.MOVE_LITERAL, castling, line)
                return

        # --- Case 2: Piece literal (white-king, B-Q, etc.) ---
        if base_word in PIECE_PREFIXES and self._peek() == "-":
            piece_lit = self._try_piece_literal(start, base_word)
            if piece_lit is not None:
                self._add_token(TokenType.PIECE_LITERAL, piece_lit, line)
                return

        # --- Case 3: Keyword ---
        if base_word in KEYWORDS:
            self._add_token(KEYWORDS[base_word], base_word, line)
            return

        # --- Case 4: Square literal [A-H][1-8] (exactly 2 chars, uppercase) ---
        if self._is_square_literal(base_word):
            self._add_token(TokenType.SQUARE_LITERAL, base_word, line)
            return

        # --- Case 5: Move literal (standard chess notation) ---
        if self._is_move_literal(base_word):
            # Consume optional trailing annotation: +, #, =, !, ?
            while not self._at_end() and self._peek() in "+#=!?":
                self._advance()
            move_text = self.source[start:self.pos]
            self._add_token(TokenType.MOVE_LITERAL, move_text, line)
            return

        # --- Case 6: Identifier ---
        self._add_token(TokenType.IDENTIFIER, base_word, line)

    # ------------------------------------------------------------------
    # Castling helper
    # ------------------------------------------------------------------

    def _try_castling(self, start: int) -> str | None:
        """
        Starting from base_word='O' with next char '-', try to match
        O-O-O (queenside) or O-O (kingside). Returns the matched string
        or None (and resets position).
        """
        saved_pos = self.pos
        saved_line = self.line

        # Try O-O-O first (longest match)
        if (self._peek() == "-" and self._peek(1) == "O"
                and self._peek(2) == "-" and self._peek(3) == "O"):
            self._advance()  # -
            self._advance()  # O
            self._advance()  # -
            self._advance()  # O
            return self.source[start:self.pos]

        # Try O-O
        if self._peek() == "-" and self._peek(1) == "O":
            self._advance()  # -
            self._advance()  # O
            return self.source[start:self.pos]

        # No match — restore position
        self.pos = saved_pos
        self.line = saved_line
        return None

    # ------------------------------------------------------------------
    # Piece literal helper
    # ------------------------------------------------------------------

    def _try_piece_literal(self, start: int, prefix: str) -> str | None:
        """
        Starting from prefix (e.g. 'white', 'B') with next char '-',
        try to match prefix-pieceName. Returns the matched string or None.
        """
        saved_pos = self.pos
        saved_line = self.line

        self._advance()  # consume '-'

        # Read the piece name part
        piece_start = self.pos
        while not self._at_end() and (self._peek().isalpha() or self._peek() == "_"):
            self._advance()

        piece_name = self.source[piece_start:self.pos]

        if piece_name in PIECE_NAMES:
            return self.source[start:self.pos]

        # Not a valid piece name — restore
        self.pos = saved_pos
        self.line = saved_line
        return None

    # ------------------------------------------------------------------
    # Square literal check
    # ------------------------------------------------------------------

    @staticmethod
    def _is_square_literal(word: str) -> bool:
        """Check if word is a square literal: [A-H][1-8], exactly 2 chars."""
        return (len(word) == 2
                and word[0] in "ABCDEFGH"
                and word[1] in "12345678")

    # ------------------------------------------------------------------
    # Move literal check
    # ------------------------------------------------------------------

    @staticmethod
    def _is_move_literal(word: str) -> bool:
        """
        Check if word matches standard chess move notation (excluding castling,
        which is handled separately).

        Patterns matched:
          - [a-h][1-8]                      pawn move (e4, d5)
          - [a-h]x[a-h][1-8]               pawn capture (cxd5, exd5)
          - [KQRBN][a-h][1-8]              piece move (Nf3, Bc4)
          - [KQRBN]x[a-h][1-8]             piece capture (Qxd5, Nxe5)
          - [KQRBN][a-h][a-h][1-8]         disambiguated piece move (Rac1)
          - [KQRBN][1-8][a-h][1-8]         disambiguated piece move (R1a3)
          - [KQRBN][a-h]x[a-h][1-8]        disambiguated piece capture (Raxc1)
          - [KQRBN][1-8]x[a-h][1-8]        disambiguated piece capture (R1xc3)
        """
        files = set("abcdefgh")
        ranks = set("12345678")

        n = len(word)
        if n < 2:
            return False

        # Pawn move: [a-h][1-8]
        if n == 2 and word[0] in files and word[1] in ranks:
            return True

        # Pawn capture: [a-h]x[a-h][1-8]
        if n == 4 and word[0] in files and word[1] == "x" and word[2] in files and word[3] in ranks:
            return True

        # Piece moves/captures
        if word[0] in PIECE_LETTERS:
            rest = word[1:]

            # [KQRBN][a-h][1-8]  — piece move
            if len(rest) == 2 and rest[0] in files and rest[1] in ranks:
                return True

            # [KQRBN]x[a-h][1-8] — piece capture
            if len(rest) == 3 and rest[0] == "x" and rest[1] in files and rest[2] in ranks:
                return True

            # [KQRBN][a-h][a-h][1-8] — disambiguated by file
            if len(rest) == 3 and rest[0] in files and rest[1] in files and rest[2] in ranks:
                return True

            # [KQRBN][1-8][a-h][1-8] — disambiguated by rank
            if len(rest) == 3 and rest[0] in ranks and rest[1] in files and rest[2] in ranks:
                return True

            # [KQRBN][a-h]x[a-h][1-8] — disambiguated capture by file
            if len(rest) == 4 and rest[0] in files and rest[1] == "x" and rest[2] in files and rest[3] in ranks:
                return True

            # [KQRBN][1-8]x[a-h][1-8] — disambiguated capture by rank
            if len(rest) == 4 and rest[0] in ranks and rest[1] == "x" and rest[2] in files and rest[3] in ranks:
                return True

        return False
