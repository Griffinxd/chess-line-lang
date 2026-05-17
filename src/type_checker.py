"""
Static type checker for the CLL (Chess Language).

Operates on the AST produced by the parser. Enforces semantic
correctness and type compatibility as specified in docs/type-checker.md.
"""

from enum import Enum, auto

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
from errors import TypeCheckError


# =====================================================================
# CLL Types
# =====================================================================

class CllType(Enum):
    """All types in the ChessLineLang type system."""
    BOARD = auto()
    MOVE = auto()
    PIECE = auto()
    COLOR = auto()
    SQUARE = auto()
    STRING = auto()
    EVAL_SCORE = auto()
    MOVE_SEQUENCE = auto()
    PREMOVE = auto()
    VOID = auto()


# Types that are valid arguments to print()
_PRINTABLE_TYPES = frozenset({
    CllType.BOARD,
    CllType.MOVE,
    CllType.PIECE,
    CllType.COLOR,
    CllType.STRING,
    CllType.SQUARE,
    CllType.EVAL_SCORE,
})


# =====================================================================
# Lexical-Scoped Symbol Table
# =====================================================================

class SymbolTable:
    """
    A stack of scopes for lexical scoping.

    - ``declare`` registers a name in the **current** (top) scope.
      Redeclaration in the same scope is an error; shadowing in an
      inner scope is allowed.
    - ``lookup`` searches from the top scope downward.
      If the name is not found anywhere, it raises TypeCheckError
      (declaration-before-use).
    """

    def __init__(self):
        # Each element is a dict[str, CllType]
        self._scopes: list[dict[str, CllType]] = [{}]  # global scope

    def enter_scope(self):
        """Push a new empty scope onto the stack."""
        self._scopes.append({})

    def exit_scope(self):
        """Pop the top scope."""
        self._scopes.pop()

    def declare(self, name: str, cll_type: CllType, line: int):
        """
        Register *name* with *cll_type* in the current scope.
        Raises TypeCheckError if *name* is already declared in
        the **same** scope.
        """
        top = self._scopes[-1]
        if name in top:
            raise TypeCheckError(
                f"Redeclaration of '{name}' in the same scope", line
            )
        top[name] = cll_type

    def lookup(self, name: str, line: int) -> CllType:
        """
        Find *name* starting from the innermost scope.
        Raises TypeCheckError if not found (declaration before use).
        """
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        raise TypeCheckError(
            f"Use of undeclared variable '{name}'", line
        )


# =====================================================================
# Type Checker
# =====================================================================

class TypeChecker:
    """
    Walks an AST and validates semantic / type rules.

    Usage::

        TypeChecker().check(program_node)

    Raises ``TypeCheckError`` on the first violation found.
    """

    def __init__(self):
        self.symbols = SymbolTable()
        # Depth counter: > 0 means we are inside a position block or
        # line branch, so `this` is valid.
        self._position_depth: int = 0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def check(self, program: ProgramNode):
        """Type-check an entire program."""
        for stmt in program.statements:
            self._check_statement(stmt)

    # ------------------------------------------------------------------
    # Statement checking
    # ------------------------------------------------------------------

    def _check_statement(self, node):
        """Dispatch to the appropriate handler based on AST node type."""

        if isinstance(node, BoardDeclNode):
            self._check_board_decl(node)

        elif isinstance(node, ColorDeclNode):
            self._check_color_decl(node)

        elif isinstance(node, PieceDeclNode):
            self._check_piece_decl(node)

        elif isinstance(node, MoveDeclNode):
            self._check_move_decl(node)

        elif isinstance(node, PremoveDeclNode):
            self._check_premove_decl(node)

        elif isinstance(node, PositionBlockNode):
            self._check_position_block(node)

        elif isinstance(node, PrintStmtNode):
            self._check_print_stmt(node)

        elif isinstance(node, AssignmentNode):
            self._check_assignment(node)

        elif isinstance(node, SquareAssignmentNode):
            self._check_square_assignment(node)

        elif isinstance(node, ExpressionStmtNode):
            # Any expression is allowed as a statement.
            self._type_of(node.expr)

        elif isinstance(node, LineBranchNode):
            self._check_line_branch(node)

        else:
            # Safety net — should not be reached for well-formed ASTs.
            raise TypeCheckError(
                f"Unknown statement node: {type(node).__name__}", node.line
            )

    # ------------------------------------------------------------------
    # Declaration handlers
    # ------------------------------------------------------------------

    def _check_board_decl(self, node: BoardDeclNode):
        # Initializer (if present) must be a board-init construct:
        #   BoardInitNode  → 'starting' or 'empty'
        #   StringLiteralNode → FEN string (dedicated construct, not coercion)
        # Both are accepted without further type checking.
        if node.init is not None:
            if not isinstance(node.init, (BoardInitNode, StringLiteralNode)):
                init_type = self._type_of(node.init)
                if init_type != CllType.BOARD:
                    raise TypeCheckError(
                        "Board initializer must be 'starting', 'empty', "
                        "or a FEN string",
                        node.line,
                    )
        for name in node.names:
            self.symbols.declare(name, CllType.BOARD, node.line)

    def _check_color_decl(self, node: ColorDeclNode):
        val_type = self._type_of(node.value)
        if val_type != CllType.COLOR:
            raise TypeCheckError(
                f"Color declaration requires COLOR on RHS, got {val_type.name}",
                node.line,
            )
        self.symbols.declare(node.name, CllType.COLOR, node.line)

    def _check_piece_decl(self, node: PieceDeclNode):
        val_type = self._type_of(node.value)
        if val_type != CllType.PIECE:
            raise TypeCheckError(
                f"Piece declaration requires PIECE on RHS, got {val_type.name}",
                node.line,
            )
        self.symbols.declare(node.name, CllType.PIECE, node.line)

    def _check_move_decl(self, node: MoveDeclNode):
        expr_type = self._type_of(node.expr)
        if expr_type != CllType.MOVE:
            raise TypeCheckError(
                f"Move declaration requires MOVE on RHS, got {expr_type.name}",
                node.line,
            )
        self.symbols.declare(node.name, CllType.MOVE, node.line)

    def _check_premove_decl(self, node: PremoveDeclNode):
        self.symbols.declare(node.name, CllType.PREMOVE, node.line)
        # Body items live in their own scope.
        self.symbols.enter_scope()
        for item in node.body:
            if isinstance(item, PremoveItemNode):
                # The inner item should be a move literal.
                self._type_of(item.item)
            else:
                self._type_of(item)
        self.symbols.exit_scope()

    # ------------------------------------------------------------------
    # Block / branch handlers
    # ------------------------------------------------------------------

    def _check_position_block(self, node: PositionBlockNode):
        board_type = self.symbols.lookup(node.board_name, node.line)
        if board_type != CllType.BOARD:
            raise TypeCheckError(
                f"Position block target '{node.board_name}' must be BOARD, "
                f"got {board_type.name}",
                node.line,
            )
        self.symbols.enter_scope()
        self._position_depth += 1
        for item in node.moves:
            self._check_move_item(item)
        self._position_depth -= 1
        self.symbols.exit_scope()

    def _check_line_branch(self, node: LineBranchNode):
        if self._position_depth == 0:
            raise TypeCheckError(
                "Line branch is only allowed inside a position block or "
                "another line branch",
                node.line,
            )
        # Branch move is always a move literal — type MOVE, always valid.
        self.symbols.enter_scope()
        self._position_depth += 1
        for item in node.moves:
            self._check_move_item(item)
        self._position_depth -= 1
        self.symbols.exit_scope()

    def _check_move_item(self, node):
        """Check a single item inside a position block or line branch."""
        # Move items can be declarations, assignments, line branches,
        # print statements, or expression statements.
        self._check_statement(node)

    # ------------------------------------------------------------------
    # Print
    # ------------------------------------------------------------------

    def _check_print_stmt(self, node: PrintStmtNode):
        expr_type = self._type_of(node.expr)
        if expr_type not in _PRINTABLE_TYPES:
            raise TypeCheckError(
                f"Cannot print value of type {expr_type.name}",
                node.line,
            )

    # ------------------------------------------------------------------
    # Assignments
    # ------------------------------------------------------------------

    def _check_assignment(self, node: AssignmentNode):
        if isinstance(node.target, BoardAttributeNode):
            self._check_board_attr_assignment(node)
        elif isinstance(node.target, IdentifierNode):
            self._check_simple_assignment(node)
        else:
            raise TypeCheckError(
                f"Invalid assignment target: {type(node.target).__name__}",
                node.line,
            )

    def _check_simple_assignment(self, node: AssignmentNode):
        target_name = node.target.name
        target_type = self.symbols.lookup(target_name, node.line)
        rhs_type = self._type_of(node.value)

        # Special rule: BOARD <= MOVE_SEQUENCE is allowed.
        if target_type == CllType.BOARD and rhs_type == CllType.MOVE_SEQUENCE:
            return

        if target_type != rhs_type:
            raise TypeCheckError(
                f"Cannot assign {rhs_type.name} to variable '{target_name}' "
                f"of type {target_type.name}",
                node.line,
            )

    def _check_board_attr_assignment(self, node: AssignmentNode):
        attr_node: BoardAttributeNode = node.target
        board_type = self.symbols.lookup(attr_node.board_name, node.line)
        if board_type != CllType.BOARD:
            raise TypeCheckError(
                f"Attribute access target '{attr_node.board_name}' must be "
                f"BOARD, got {board_type.name}",
                node.line,
            )
        rhs_type = self._type_of(node.value)
        if rhs_type != CllType.COLOR:
            raise TypeCheckError(
                f"Board attribute (turn/color) assignment requires COLOR on "
                f"RHS, got {rhs_type.name}",
                node.line,
            )

    def _check_square_assignment(self, node: SquareAssignmentNode):
        board_type = self.symbols.lookup(node.board_name, node.line)
        if board_type != CllType.BOARD:
            raise TypeCheckError(
                f"Square assignment target '{node.board_name}' must be "
                f"BOARD, got {board_type.name}",
                node.line,
            )
        rhs_type = self._type_of(node.value)
        if rhs_type != CllType.PIECE:
            raise TypeCheckError(
                f"Square assignment requires PIECE on RHS, got {rhs_type.name}",
                node.line,
            )

    # ------------------------------------------------------------------
    # Expression typing
    # ------------------------------------------------------------------

    def _type_of(self, node) -> CllType:
        """Return the CllType of an expression node."""

        if isinstance(node, IdentifierNode):
            return self.symbols.lookup(node.name, node.line)

        if isinstance(node, StringLiteralNode):
            return CllType.STRING

        if isinstance(node, ColorLiteralNode):
            return CllType.COLOR

        if isinstance(node, PieceLiteralNode):
            return CllType.PIECE

        if isinstance(node, SquareLiteralNode):
            return CllType.SQUARE

        if isinstance(node, MoveLiteralNode):
            return CllType.MOVE

        if isinstance(node, BoardInitNode):
            return CllType.BOARD

        if isinstance(node, ThisNode):
            if self._position_depth == 0:
                raise TypeCheckError(
                    "'this' is only valid inside a position block or "
                    "line branch",
                    node.line,
                )
            return CllType.BOARD

        if isinstance(node, BoardAttributeNode):
            board_type = self.symbols.lookup(node.board_name, node.line)
            if board_type != CllType.BOARD:
                raise TypeCheckError(
                    f"Attribute access target '{node.board_name}' must be "
                    f"BOARD, got {board_type.name}",
                    node.line,
                )
            return CllType.COLOR

        if isinstance(node, SquareAccessNode):
            board_type = self.symbols.lookup(node.board_name, node.line)
            if board_type != CllType.BOARD:
                raise TypeCheckError(
                    f"Square access target '{node.board_name}' must be "
                    f"BOARD, got {board_type.name}",
                    node.line,
                )
            return CllType.PIECE

        if isinstance(node, EvalCallNode):
            arg_type = self._type_of(node.expr)
            if arg_type != CllType.BOARD:
                raise TypeCheckError(
                    f"eval() argument must be BOARD, got {arg_type.name}",
                    node.line,
                )
            return CllType.EVAL_SCORE

        if isinstance(node, EvalMethodCallNode):
            if len(node.args) != 1:
                raise TypeCheckError(
                    "eval.move() expects exactly one argument", node.line
                )
            arg_type = self._type_of(node.args[0])
            if arg_type != CllType.BOARD:
                raise TypeCheckError(
                    f"eval.move() argument must be BOARD, got {arg_type.name}",
                    node.line,
                )
            return CllType.MOVE

        if isinstance(node, PremoveCallNode):
            callee_type = self.symbols.lookup(node.name, node.line)
            if callee_type != CllType.PREMOVE:
                raise TypeCheckError(
                    f"'{node.name}' is not a premove (got {callee_type.name})",
                    node.line,
                )
            # Validate arguments: either a single PREMOVE identifier,
            # or a one-side move sequence (move literals).
            for arg in node.args:
                if isinstance(arg, PremoveItemNode):
                    inner = arg.item
                else:
                    inner = arg
                inner_type = self._type_of(inner)
                if inner_type not in (CllType.PREMOVE, CllType.MOVE):
                    raise TypeCheckError(
                        f"Premove call argument must be PREMOVE or MOVE, "
                        f"got {inner_type.name}",
                        node.line,
                    )
            return CllType.MOVE_SEQUENCE

        raise TypeCheckError(
            f"Cannot determine type of node: {type(node).__name__}",
            node.line,
        )
