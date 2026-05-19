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
            # TODO (Batch 3): line branch execution
            raise RuntimeCllError(
                "Line branch execution is not yet implemented", node.line
            )

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
    # Position block (Batch 3 stub)
    # ------------------------------------------------------------------

    def _exec_position_block(self, node: PositionBlockNode):
        """Execute a position block. Placeholder until Batch 3."""
        # TODO (Batch 3): push moves onto a board copy, handle branches.
        raise RuntimeCllError(
            "Position block execution is not yet implemented", node.line
        )

    # ------------------------------------------------------------------
    # Square assignment (Batch 4 stub)
    # ------------------------------------------------------------------

    def _exec_square_assignment(self, node: SquareAssignmentNode):
        """Execute a square assignment. Placeholder until Batch 4."""
        # TODO (Batch 4): place piece on board square.
        raise RuntimeCllError(
            "Square assignment is not yet implemented", node.line
        )

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

        # --- this (Batch 3) ---
        if isinstance(node, ThisNode):
            raise RuntimeCllError(
                "'this' is only valid during position block execution "
                "(not yet implemented)",
                node.line,
            )

        # --- Board attribute access ---
        if isinstance(node, BoardAttributeNode):
            return self._eval_board_attr_access(node)

        # --- Square access (Batch 4) ---
        if isinstance(node, SquareAccessNode):
            raise RuntimeCllError(
                "Square access is not yet implemented", node.line
            )

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

        # --- Premove call (Batch 5) ---
        if isinstance(node, PremoveCallNode):
            raise RuntimeCllError(
                "Premove call execution is not yet implemented", node.line
            )

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
