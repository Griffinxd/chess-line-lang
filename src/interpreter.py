"""
Tree-walking interpreter for the CLL (Chess Language).

Executes the AST produced by the parser after type-checking passes.
This module implements the runtime phase of the pipeline:

    Source → Lexer → Parser → TypeChecker → **Interpreter**
"""

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
from errors import RuntimeCllError, UninitializedVariableError


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
        # Values may be Python strings, the UNINITIALIZED sentinel,
        # or domain objects added in later batches.
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
            # TODO (Batch 2): evaluate board initializers (starting/empty/FEN)
            init_val = self._eval_board_init(node.init, node.line)
            for name in node.names:
                self._env[name] = init_val
        else:
            for name in node.names:
                self._env[name] = UNINITIALIZED

    def _eval_board_init(self, init_node, line: int):
        """Evaluate a board initializer. Placeholder until Batch 2."""
        if isinstance(init_node, BoardInitNode):
            # 'starting' or 'empty' — will become chess.Board() objects.
            # For now, store as a descriptive string placeholder.
            return f"<board:{init_node.value}>"
        if isinstance(init_node, StringLiteralNode):
            # FEN string — will be validated in Batch 2.
            return f"<board:FEN:{init_node.value}>"
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
            # The type checker guarantees the variable was declared.
            self._env[name] = value

        elif isinstance(node.target, BoardAttributeNode):
            # TODO (Batch 2): board attribute assignment (pos.turn <= white)
            raise RuntimeCllError(
                "Board attribute assignment is not yet implemented",
                node.line,
            )
        else:
            raise RuntimeCllError(
                f"Invalid assignment target: {type(node.target).__name__}",
                node.line,
            )

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

        # --- Board attribute access (Batch 2) ---
        if isinstance(node, BoardAttributeNode):
            raise RuntimeCllError(
                "Board attribute access is not yet implemented", node.line
            )

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
