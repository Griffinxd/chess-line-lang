"""
Tree-walking interpreter for the CLL (Chess Language).

Executes the AST produced by the parser after type-checking passes.
This module implements the runtime phase of the pipeline:

    Source → Lexer → Parser → TypeChecker → **Interpreter**
"""

import chess

from ast_nodes import (
    ProgramNode,
    BoardDeclNode, BoardInitNode, ColorDeclNode, PieceDeclNode,
    MoveDeclNode, PremoveDeclNode,
    PositionBlockNode, PrintStmtNode, ExpressionStmtNode,
    AssignmentNode, BoardAttributeNode, SquareAccessNode,
    SquareAssignmentNode,
    PremoveItemNode, MoveLiteralNode, LineBranchNode, PremoveCallNode,
    IdentifierNode, StringLiteralNode, ColorLiteralNode,
    PieceLiteralNode, SquareLiteralNode, ThisNode,
    EvalCallNode, EvalMethodCallNode,
)
from errors import (
    RuntimeCllError, UninitializedVariableError, InvalidFENError,
    IllegalMoveError, EmptySquareError, IllegalBoardError,
    IncompatiblePremoveError,
)


# =====================================================================
# Sentinel for uninitialized variables
# =====================================================================

class _Uninitialized:
    """Marker for variables that have been declared but not yet assigned."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "<UNINITIALIZED>"


UNINITIALIZED = _Uninitialized()


# =====================================================================
# Color-string helpers
# =====================================================================

# Map CLL color literal strings (case-insensitive) to chess.WHITE/BLACK.
_COLOR_TO_CHESS = {
    "white": chess.WHITE,
    "black": chess.BLACK,
}

# Map chess.WHITE/BLACK back to a display string.
_CHESS_TO_COLOR_STR = {
    chess.WHITE: "white",
    chess.BLACK: "black",
}

# Attribute aliases that all mean "turn".
_TURN_ALIASES = frozenset({"turn", "tr", "color", "cl"})


# =====================================================================
# Piece-conversion helpers
# =====================================================================

# Map CLL color prefix (case-insensitive) → chess.WHITE / chess.BLACK.
_PIECE_COLOR_PREFIX = {
    "w":     chess.WHITE,
    "white": chess.WHITE,
    "b":     chess.BLACK,
    "black": chess.BLACK,
}

# Map CLL piece name (case-insensitive) → chess piece type constant.
_PIECE_NAME_TO_TYPE = {
    "king":   chess.KING,
    "queen":  chess.QUEEN,
    "rook":   chess.ROOK,
    "bishop": chess.BISHOP,
    "knight": chess.KNIGHT,
    "pawn":   chess.PAWN,
    "k":      chess.KING,
    "q":      chess.QUEEN,
    "r":      chess.ROOK,
    "b":      chess.BISHOP,
    "n":      chess.KNIGHT,
    "p":      chess.PAWN,
}

# Reverse map: chess piece type → canonical CLL name (lowercase).
_PIECE_TYPE_TO_NAME = {
    chess.KING:   "king",
    chess.QUEEN:  "queen",
    chess.ROOK:   "rook",
    chess.BISHOP: "bishop",
    chess.KNIGHT: "knight",
    chess.PAWN:   "pawn",
}

# Reverse map: chess color → CLL prefix.
_CHESS_COLOR_TO_PREFIX = {
    chess.WHITE: "W",
    chess.BLACK: "B",
}


def _cll_piece_to_chess(piece_str: str, line: int) -> chess.Piece:
    """
    Convert a CLL piece literal string to a ``chess.Piece``.

    Accepted formats: ``W-king``, ``B-Q``, ``white-rook``, etc.
    """
    parts = piece_str.split("-", 1)
    if len(parts) != 2:
        raise RuntimeCllError(
            f"Invalid piece literal: '{piece_str}'", line
        )
    prefix, name = parts
    color = _PIECE_COLOR_PREFIX.get(prefix.lower())
    ptype = _PIECE_NAME_TO_TYPE.get(name.lower())
    if color is None or ptype is None:
        raise RuntimeCllError(
            f"Invalid piece literal: '{piece_str}'", line
        )
    return chess.Piece(ptype, color)


def _chess_piece_to_cll(piece: chess.Piece) -> str:
    """
    Convert a ``chess.Piece`` back to its canonical CLL string.

    Example: ``chess.Piece(chess.KING, chess.WHITE)`` → ``"W-king"``.
    """
    prefix = _CHESS_COLOR_TO_PREFIX[piece.color]
    name = _PIECE_TYPE_TO_NAME[piece.piece_type]
    return f"{prefix}-{name}"


# =====================================================================
# Square-conversion helpers
# =====================================================================

# Map CLL square literal (e.g. "E1") → chess.Square int.
def _cll_square_to_chess(square_str: str, line: int) -> chess.Square:
    """
    Convert a CLL square literal to a ``chess.Square``.

    CLL uses uppercase file letters: ``E1``, ``A8``, etc.
    python-chess uses lowercase: ``chess.E1``, etc.
    """
    try:
        return chess.parse_square(square_str.lower())
    except ValueError:
        raise RuntimeCllError(
            f"Invalid square: '{square_str}'", line
        )


# =====================================================================
# Interpreter
# =====================================================================

class Interpreter:
    """
    Tree-walking interpreter for CLL.

    Usage::

        interpreter = Interpreter()
        interpreter.execute(program_node)

    Raises ``RuntimeCllError`` (or a subclass) on runtime violations.
    """

    def __init__(self):
        # Flat runtime environment — maps variable names to values.
        # BOARD values are chess.Board objects; color values are strings
        # like "white"/"black"; other literals are plain Python strings.
        self._env: dict[str, object] = {}

        # Premove table — maps premove names to their AST declarations.
        # Populated during execution and used for premove call expansion
        # (Batch 5).
        self._premoves: dict[str, PremoveDeclNode] = {}

        # Board context stack — tracks the "current board" during
        # position block / line branch execution.  `this` evaluates to
        # a copy of the top-of-stack board.  Empty outside of any
        # position block.
        self._board_stack: list[chess.Board] = []

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def execute(self, program: ProgramNode):
        """Execute an entire CLL program."""
        for stmt in program.statements:
            self._exec_statement(stmt)

    # ------------------------------------------------------------------
    # Statement dispatcher
    # ------------------------------------------------------------------

    def _exec_statement(self, node):
        """Dispatch to the appropriate handler based on AST node type."""

        if isinstance(node, BoardDeclNode):
            self._exec_board_decl(node)

        elif isinstance(node, ColorDeclNode):
            self._exec_color_decl(node)

        elif isinstance(node, PieceDeclNode):
            self._exec_piece_decl(node)

        elif isinstance(node, MoveDeclNode):
            self._exec_move_decl(node)

        elif isinstance(node, PremoveDeclNode):
            self._exec_premove_decl(node)

        elif isinstance(node, PrintStmtNode):
            self._exec_print_stmt(node)

        elif isinstance(node, AssignmentNode):
            self._exec_assignment(node)

        elif isinstance(node, PositionBlockNode):
            self._exec_position_block(node)

        elif isinstance(node, SquareAssignmentNode):
            self._exec_square_assignment(node)

        elif isinstance(node, ExpressionStmtNode):
            # Evaluate for side effects (e.g. premove calls as statements).
            self._eval_expr(node.expr)

        elif isinstance(node, LineBranchNode):
            self._exec_line_branch(node)

        else:
            raise RuntimeCllError(
                f"Unknown statement node: {type(node).__name__}", node.line
            )

    # ------------------------------------------------------------------
    # Declaration handlers
    # ------------------------------------------------------------------

    def _exec_board_decl(self, node: BoardDeclNode):
        """Declare board variable(s), optionally with an initializer."""
        if node.init is not None:
            init_val = self._eval_board_init(node.init, node.line)
            for name in node.names:
                # Each declared name gets its own independent copy.
                self._env[name] = init_val.copy()
        else:
            for name in node.names:
                self._env[name] = UNINITIALIZED

    def _eval_board_init(self, init_node, line: int) -> chess.Board:
        """
        Evaluate a board initializer and return a chess.Board.

        - 'starting'        → chess.Board()
        - 'empty'           → chess.Board(None)
        - FEN string        → chess.Board(fen), raises InvalidFENError on failure
        """
        if isinstance(init_node, BoardInitNode):
            if init_node.value == "starting":
                return chess.Board()
            if init_node.value == "empty":
                return chess.Board(None)
            raise RuntimeCllError(
                f"Unknown board init keyword: {init_node.value}", line
            )

        if isinstance(init_node, StringLiteralNode):
            # The lexer stores the string with surrounding quotes.
            fen = init_node.value.strip('"')
            try:
                board = chess.Board(fen)
            except ValueError as e:
                raise InvalidFENError(
                    f"Invalid FEN string: {fen}", line
                ) from e
            return board

        raise RuntimeCllError(
            f"Unexpected board initializer: {type(init_node).__name__}", line
        )

    def _exec_color_decl(self, node: ColorDeclNode):
        """Declare a color variable with its initializer value."""
        value = self._eval_expr(node.value)
        self._env[node.name] = value

    def _exec_piece_decl(self, node: PieceDeclNode):
        """Declare a piece variable with its initializer value."""
        value = self._eval_expr(node.value)
        self._env[node.name] = value

    def _exec_move_decl(self, node: MoveDeclNode):
        """Declare a move variable with its initializer value."""
        value = self._eval_expr(node.expr)
        self._env[node.name] = value

    def _exec_premove_decl(self, node: PremoveDeclNode):
        """Register a premove declaration in the premove table."""
        # Store the AST node for later expansion (Batch 5).
        self._premoves[node.name] = node
        # Also register in the environment so identifier lookups resolve.
        self._env[node.name] = f"<premove:{node.name}>"

    # ------------------------------------------------------------------
    # Print
    # ------------------------------------------------------------------

    def _exec_print_stmt(self, node: PrintStmtNode):
        """Evaluate the expression and print its runtime representation."""
        value = self._eval_expr(node.expr)
        print(value)

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    def _exec_assignment(self, node: AssignmentNode):
        """Execute a simple or board-attribute assignment."""
        if isinstance(node.target, IdentifierNode):
            if isinstance(node.value, PremoveCallNode):
                self._exec_premove_assignment(node)
                return

            value = self._eval_expr(node.value)
            name = node.target.name
            # Board assignment must copy to prevent aliasing.
            if isinstance(value, chess.Board):
                value = value.copy()
            # The type checker guarantees the variable was declared.
            self._env[name] = value

        elif isinstance(node.target, BoardAttributeNode):
            self._exec_board_attr_assignment(node)

        else:
            raise RuntimeCllError(
                f"Invalid assignment target: {type(node.target).__name__}",
                node.line,
            )

    def _exec_board_attr_assignment(self, node: AssignmentNode):
        """
        Execute a board attribute assignment: pos.turn <= white/black.

        Attribute aliases: turn, tr, color, cl.
        """
        attr_node: BoardAttributeNode = node.target
        board = self._lookup_variable(attr_node.board_name, node.line)

        if not isinstance(board, chess.Board):
            raise RuntimeCllError(
                f"Attribute assignment target '{attr_node.board_name}' is not "
                f"a board",
                node.line,
            )

        attr = attr_node.attribute.lower()
        if attr not in _TURN_ALIASES:
            raise RuntimeCllError(
                f"Unknown board attribute: {attr_node.attribute}", node.line
            )

        rhs = self._eval_expr(node.value)
        chess_color = _COLOR_TO_CHESS.get(
            rhs.lower() if isinstance(rhs, str) else None
        )
        if chess_color is None:
            raise RuntimeCllError(
                f"Board attribute (turn/color) requires 'white' or 'black', "
                f"got '{rhs}'",
                node.line,
            )
        board.turn = chess_color

    # ------------------------------------------------------------------
    # Position block execution
    # ------------------------------------------------------------------

    def _exec_position_block(self, node: PositionBlockNode):
        """
        Execute a position block: pos.{ move_items... }

        Moves are applied sequentially to the actual board stored in
        the runtime environment.  Line branches operate on copied
        board states and never mutate the mainline board.
        """
        board = self._lookup_variable(node.board_name, node.line)

        if not isinstance(board, chess.Board):
            raise RuntimeCllError(
                f"Position block target '{node.board_name}' is not a board",
                node.line,
            )

        # Validate board legality before executing chess-semantic moves.
        self._assert_valid_board(board, node.line)

        # Push the board onto the context stack so `this` resolves.
        self._board_stack.append(board)
        try:
            for item in node.moves:
                self._exec_move_item(item, board)
        finally:
            self._board_stack.pop()

    def _exec_move_item(self, node, board: chess.Board):
        """
        Execute a single item inside a position block or line branch.

        Move items can be:
        - MoveLiteralNode / ExpressionStmtNode wrapping a MoveLiteral/Identifier
          → push the move on the board
        - LineBranchNode → execute on a copied board
        - AssignmentNode, PrintStmtNode, declarations → delegate to statement
        """
        # --- Move literal: push move on board ---
        if isinstance(node, MoveLiteralNode):
            self._push_san(board, node.notation, node.line)
            return

        # --- Expression statement wrapping a move literal or identifier ---
        if isinstance(node, ExpressionStmtNode):
            if isinstance(node.expr, MoveLiteralNode):
                self._push_san(board, node.expr.notation, node.expr.line)
                return
            if isinstance(node.expr, IdentifierNode):
                value = self._lookup_variable(node.expr.name, node.expr.line)
                # If the identifier resolves to a move string, push it.
                if isinstance(value, str) and not value.startswith("<"):
                    self._push_san(board, value, node.expr.line)
                    return
            # Other expression statements: evaluate for side effects.
            self._eval_expr(node.expr)
            return

        # --- Line branch: execute on a copy ---
        if isinstance(node, LineBranchNode):
            self._exec_line_branch_on(node, board)
            return

        # --- All other statements (assignments, prints, declarations) ---
        self._exec_statement(node)

    # ------------------------------------------------------------------
    # Line branch execution
    # ------------------------------------------------------------------

    def _exec_line_branch(self, node: LineBranchNode):
        """
        Execute a line branch at statement level.

        This only happens when a line branch is used as a standalone
        statement (dispatched from _exec_statement).  In that context,
        we use the board on top of the context stack.
        """
        if not self._board_stack:
            raise RuntimeCllError(
                "Line branch outside of a position block", node.line
            )
        parent_board = self._board_stack[-1]
        self._exec_line_branch_on(node, parent_board)

    def _exec_line_branch_on(self, node: LineBranchNode,
                              parent_board: chess.Board):
        """
        Execute a line branch against a given parent board.

        1. Copy the parent board.
        2. Push the branch move onto the copy.
        3. Execute the branch body on the copy.
        4. The parent board is NEVER mutated.
        """
        branch_board = parent_board.copy()

        # Push the branch move.
        self._push_san(branch_board, node.move_lit, node.line)

        # Push the branch board onto the context stack so `this` and
        # nested branches resolve against it.
        self._board_stack.append(branch_board)
        try:
            for item in node.moves:
                self._exec_move_item(item, branch_board)
        finally:
            self._board_stack.pop()

    # ------------------------------------------------------------------
    # SAN move execution helper
    # ------------------------------------------------------------------

    def _push_san(self, board: chess.Board, san: str, line: int):
        """
        Push a SAN move onto a board.
        Raises IllegalMoveError if the move is not legal.
        """
        try:
            board.push_san(san)
        except (chess.IllegalMoveError, chess.InvalidMoveError,
                chess.AmbiguousMoveError, ValueError) as e:
            raise IllegalMoveError(
                f"Illegal move '{san}'", line
            ) from e

    # ------------------------------------------------------------------
    # Premove execution (Batch 5A)
    # ------------------------------------------------------------------

    def _exec_premove_assignment(self, node: AssignmentNode):
        """
        Execute an assignment of a premove sequence to a board.
        pos <= white_line(black_line)
        """
        name = node.target.name
        board = self._lookup_variable(name, node.line)
        
        if not isinstance(board, chess.Board):
            raise RuntimeCllError(f"Target '{name}' is not a board", node.line)
            
        self._assert_valid_board(board, node.line)
        
        merged_moves, is_named_merge = self._eval_premove_call(node.value)
        
        new_board = board.copy()
        for san in merged_moves:
            try:
                new_board.push_san(san)
            except (chess.IllegalMoveError, chess.InvalidMoveError,
                    chess.AmbiguousMoveError, ValueError) as e:
                if is_named_merge:
                    raise IncompatiblePremoveError(
                        "Incompatible premove lines", node.value.line
                    ) from e
                else:
                    raise IllegalMoveError(
                        f"Illegal move '{san}'", node.value.line
                    ) from e
                    
        self._env[name] = new_board

    def _expand_premove(self, name: str, line: int) -> list[str]:
        """Expand a named premove into a list of SAN strings."""
        if name not in self._premoves:
            raise RuntimeCllError(f"Undefined premove '{name}'", line)
        
        decl = self._premoves[name]
        moves = []
        for item in decl.body:
            inner = item.item if isinstance(item, PremoveItemNode) else item
            if isinstance(inner, MoveLiteralNode):
                moves.append(inner.notation)
            else:
                moves.append(str(self._eval_expr(inner)))
        return moves

    def _eval_premove_call(self, node: PremoveCallNode) -> tuple[list[str], bool]:
        """
        Expand and interleave a premove call.
        Returns (merged_moves_list, is_named_merge)
        """
        base_moves = self._expand_premove(node.name, node.line)
        arg_moves = []
        is_named_merge = False

        if node.args:
            first_arg = node.args[0].item if isinstance(node.args[0], PremoveItemNode) else node.args[0]
            if isinstance(first_arg, IdentifierNode):
                arg_moves = self._expand_premove(first_arg.name, first_arg.line)
                is_named_merge = True
            else:
                for arg in node.args:
                    inner = arg.item if isinstance(arg, PremoveItemNode) else arg
                    if isinstance(inner, MoveLiteralNode):
                        arg_moves.append(inner.notation)
                    else:
                        arg_moves.append(str(self._eval_expr(inner)))

        merged = []
        max_len = max(len(base_moves), len(arg_moves))
        for i in range(max_len):
            if i < len(base_moves):
                merged.append(base_moves[i])
            if i < len(arg_moves):
                merged.append(arg_moves[i])

        return merged, is_named_merge

    # ------------------------------------------------------------------
    # Square assignment
    # ------------------------------------------------------------------

    def _exec_square_assignment(self, node: SquareAssignmentNode):
        """
        Execute a square assignment: pos.sq(E1) <= W-king.

        Places a chess.Piece on the given square of the board.
        """
        board = self._lookup_variable(node.board_name, node.line)

        if not isinstance(board, chess.Board):
            raise RuntimeCllError(
                f"Square assignment target '{node.board_name}' is not a board",
                node.line,
            )

        square = _cll_square_to_chess(node.square.value, node.line)
        piece_value = self._eval_expr(node.value)

        # Convert CLL piece string to chess.Piece.
        piece = _cll_piece_to_chess(piece_value, node.line)

        board.set_piece_at(square, piece)

    # ------------------------------------------------------------------
    # Expression evaluator
    # ------------------------------------------------------------------

    def _eval_expr(self, node):
        """Evaluate an expression node and return its runtime value."""

        # --- Identifier lookup ---
        if isinstance(node, IdentifierNode):
            return self._lookup_variable(node.name, node.line)

        # --- Literals ---
        if isinstance(node, StringLiteralNode):
            return node.value

        if isinstance(node, ColorLiteralNode):
            return node.value

        if isinstance(node, PieceLiteralNode):
            return node.value

        if isinstance(node, SquareLiteralNode):
            return node.value

        if isinstance(node, MoveLiteralNode):
            return node.notation

        if isinstance(node, BoardInitNode):
            return self._eval_board_init(node, node.line)

        # --- this ---
        if isinstance(node, ThisNode):
            if not self._board_stack:
                raise RuntimeCllError(
                    "'this' is only valid inside a position block or "
                    "line branch",
                    node.line,
                )
            # Return a COPY so the caller cannot mutate the internal board.
            return self._board_stack[-1].copy()

        # --- Board attribute access ---
        if isinstance(node, BoardAttributeNode):
            return self._eval_board_attr_access(node)

        # --- Square access ---
        if isinstance(node, SquareAccessNode):
            return self._eval_square_access(node)

        # --- eval() (Batch 5) ---
        if isinstance(node, EvalCallNode):
            raise RuntimeCllError(
                "eval() is not yet implemented", node.line
            )

        # --- eval.move() (Batch 5) ---
        if isinstance(node, EvalMethodCallNode):
            raise RuntimeCllError(
                "eval.move() is not yet implemented", node.line
            )

        # --- Premove call (Batch 5A) ---
        if isinstance(node, PremoveCallNode):
            return self._eval_premove_call(node)

        raise RuntimeCllError(
            f"Cannot evaluate node: {type(node).__name__}", node.line
        )

    # ------------------------------------------------------------------
    # Board attribute access
    # ------------------------------------------------------------------

    def _eval_board_attr_access(self, node: BoardAttributeNode):
        """
        Evaluate a board attribute read: pos.turn / pos.tr / pos.color / pos.cl.

        Returns a color string ("white" or "black").
        """
        board = self._lookup_variable(node.board_name, node.line)

        if not isinstance(board, chess.Board):
            raise RuntimeCllError(
                f"Attribute access target '{node.board_name}' is not a board",
                node.line,
            )

        attr = node.attribute.lower()
        if attr not in _TURN_ALIASES:
            raise RuntimeCllError(
                f"Unknown board attribute: {node.attribute}", node.line
            )

        return _CHESS_TO_COLOR_STR[board.turn]

    # ------------------------------------------------------------------
    # Square access
    # ------------------------------------------------------------------

    def _eval_square_access(self, node: SquareAccessNode):
        """
        Evaluate a square read: pos.sq(E1) / pos.square(A8).

        Returns a CLL piece string (e.g. "W-king").
        Raises EmptySquareError if the square is empty.
        """
        board = self._lookup_variable(node.board_name, node.line)

        if not isinstance(board, chess.Board):
            raise RuntimeCllError(
                f"Square access target '{node.board_name}' is not a board",
                node.line,
            )

        square = _cll_square_to_chess(node.square.value, node.line)
        piece = board.piece_at(square)

        if piece is None:
            raise EmptySquareError(
                f"Empty square at {node.square.value}", node.line
            )

        return _chess_piece_to_cll(piece)

    # ------------------------------------------------------------------
    # Board validity check
    # ------------------------------------------------------------------

    def _assert_valid_board(self, board: chess.Board, line: int):
        """
        Assert that a board position is valid for chess-semantic
        operations (move execution, line branches, eval, etc.).

        Manually constructed boards may be invalid (e.g. adjacent kings).
        Those boards are allowed to *exist* but not to be used for move
        execution or engine evaluation.
        """
        if not board.is_valid():
            raise IllegalBoardError(
                "Illegal board position", line
            )

    # ------------------------------------------------------------------
    # Variable lookup with uninitialized check
    # ------------------------------------------------------------------

    def _lookup_variable(self, name: str, line: int):
        """
        Look up a variable in the runtime environment.
        Raises UninitializedVariableError if the variable holds the
        UNINITIALIZED sentinel.
        """
        if name not in self._env:
            raise RuntimeCllError(
                f"Undefined variable '{name}'", line
            )
        value = self._env[name]
        if value is UNINITIALIZED:
            raise UninitializedVariableError(
                f"Use of uninitialized variable '{name}'", line
            )
        return value
