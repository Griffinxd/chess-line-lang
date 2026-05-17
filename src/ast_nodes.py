"""
AST (Abstract Syntax Tree) node definitions for the CLL (Chess Language).

Every node stores a `line` number from its originating token for error reporting.
Every node has a `dump(indent)` method that produces an indented tree string
for the --dump-ast output.
"""


class ASTNode:
    """Base class for all AST nodes."""

    def __init__(self, line: int):
        self.line = line

    def dump(self, indent: int = 0) -> str:
        raise NotImplementedError

    def _prefix(self, indent: int) -> str:
        return "  " * indent


# =====================================================================
# Root
# =====================================================================

class ProgramNode(ASTNode):
    """Root node: a program is a list of statements."""

    def __init__(self, statements: list, line: int):
        super().__init__(line)
        self.statements = statements

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}Program"]
        for stmt in self.statements:
            lines.append(stmt.dump(indent + 1))
        return "\n".join(lines)


# =====================================================================
# Declarations
# =====================================================================

class BoardDeclNode(ASTNode):
    """
    Board declaration: bd/board <identifier_list> [ <= <board_init> ]
    names: list of declared board variable names.
    init:  BoardInitNode or StringLiteralNode, or None if uninitialized.
    """

    def __init__(self, names: list, init, line: int):
        super().__init__(line)
        self.names = names       # list[str]
        self.init = init         # ASTNode | None

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}BoardDecl names={self.names}"]
        if self.init is not None:
            lines.append(self.init.dump(indent + 1))
        return "\n".join(lines)


class BoardInitNode(ASTNode):
    """
    Board initialization keyword: 'starting' or 'empty'.
    For FEN string initialization, a StringLiteralNode is used instead.
    """

    def __init__(self, value: str, line: int):
        super().__init__(line)
        self.value = value       # "starting" or "empty"

    def dump(self, indent: int = 0) -> str:
        return f"{self._prefix(indent)}BoardInit: {self.value}"


class ColorDeclNode(ASTNode):
    """Color/turn declaration: tr/turn/cl/color <id> <= <expression>"""

    def __init__(self, name: str, value, line: int):
        super().__init__(line)
        self.name = name         # variable name
        self.value = value       # ASTNode expression

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}ColorDecl: {self.name}"]
        lines.append(self.value.dump(indent + 1))
        return "\n".join(lines)


class PieceDeclNode(ASTNode):
    """Piece declaration: pc/piece <id> <= <piece_value>"""

    def __init__(self, name: str, value, line: int):
        super().__init__(line)
        self.name = name         # variable name
        self.value = value       # PieceLiteralNode | IdentifierNode

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}PieceDecl: {self.name}"]
        lines.append(self.value.dump(indent + 1))
        return "\n".join(lines)


class MoveDeclNode(ASTNode):
    """Move declaration: mv/move <id> <= <expression>"""

    def __init__(self, name: str, expr, line: int):
        super().__init__(line)
        self.name = name         # variable name
        self.expr = expr         # any expression node

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}MoveDecl: {self.name}"]
        lines.append(self.expr.dump(indent + 1))
        return "\n".join(lines)


class PremoveDeclNode(ASTNode):
    """
    Premove subprogram declaration:
        premove <name>() { [body] }
    body items are separated by DOUBLE_COMMA.
    """

    def __init__(self, name: str, body: list, line: int):
        super().__init__(line)
        self.name = name         # premove name
        self.body = body         # list[ASTNode] — move items

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}PremoveDecl: {self.name}"]
        for item in self.body:
            lines.append(item.dump(indent + 1))
        return "\n".join(lines)


# =====================================================================
# Statements
# =====================================================================

class PositionBlockNode(ASTNode):
    """
    A move sequence applied to a board: <id>.{ <move_sequence> }
    """

    def __init__(self, board_name: str, moves: list, line: int):
        super().__init__(line)
        self.board_name = board_name
        self.moves = moves       # list[ASTNode] — move items

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}PositionBlock: {self.board_name}"]
        for mv in self.moves:
            lines.append(mv.dump(indent + 1))
        return "\n".join(lines)


class PrintStmtNode(ASTNode):
    """Print statement: print( <expression> )"""

    def __init__(self, expr, line: int):
        super().__init__(line)
        self.expr = expr         # any expression node

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}PrintStmt"]
        lines.append(self.expr.dump(indent + 1))
        return "\n".join(lines)


class ExpressionStmtNode(ASTNode):
    """An expression used as a standalone statement."""

    def __init__(self, expr, line: int):
        super().__init__(line)
        self.expr = expr

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}ExpressionStmt"]
        lines.append(self.expr.dump(indent + 1))
        return "\n".join(lines)


# =====================================================================
# Assignments
# =====================================================================

class AssignmentNode(ASTNode):
    """
    Simple assignment: <id> <= <expression>
    Also used for board attribute assignment where target is a BoardAttributeNode.
    """

    def __init__(self, target, value, line: int):
        super().__init__(line)
        self.target = target     # IdentifierNode | BoardAttributeNode
        self.value = value       # any expression node

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}Assignment"]
        lines.append(self.target.dump(indent + 1))
        lines.append(self.value.dump(indent + 1))
        return "\n".join(lines)


class BoardAttributeNode(ASTNode):
    """
    Board attribute access: <id>.turn / <id>.tr / <id>.color / <id>.cl
    Used as the left-hand side of an assignment, and now in expressions.
    """

    def __init__(self, board_name: str, attribute: str, line: int):
        super().__init__(line)
        self.board_name = board_name
        self.attribute = attribute   # "turn" / "tr" / "color" / "cl"

    def dump(self, indent: int = 0) -> str:
        return f"{self._prefix(indent)}BoardAttribute: {self.board_name}.{self.attribute}"


class SquareAccessNode(ASTNode):
    """
    Square access in an expression: <id>.sq(<square_literal>) or <id>.square(<square_literal>)
    """

    def __init__(self, board_name: str, square, line: int):
        super().__init__(line)
        self.board_name = board_name
        self.square = square     # SquareLiteralNode

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}SquareAccess: {self.board_name}"]
        lines.append(self.square.dump(indent + 1))
        return "\n".join(lines)


class SquareAssignmentNode(ASTNode):
    """
    Square assignment: <id>.sq(<square_literal>) <= <piece_value>
    Places a piece on a specific square of a board.
    """

    def __init__(self, board_name: str, square, value, line: int):
        super().__init__(line)
        self.board_name = board_name
        self.square = square     # SquareLiteralNode
        self.value = value       # PieceLiteralNode | IdentifierNode

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}SquareAssignment: {self.board_name}"]
        lines.append(self.square.dump(indent + 1))
        lines.append(self.value.dump(indent + 1))
        return "\n".join(lines)


# =====================================================================
# Move Items (inside position blocks and premove bodies)
# =====================================================================

class PremoveItemNode(ASTNode):
    """
    A wrapper for an item inside a premove body or call, preserving the
    separator (COMMA or DOUBLE_COMMA) that preceded it.
    """

    def __init__(self, item, separator_before, line: int):
        super().__init__(line)
        self.item = item                     # ASTNode
        self.separator_before = separator_before # str | None

    def dump(self, indent: int = 0) -> str:
        lines = []
        if self.separator_before:
            lines.append(f"{self._prefix(indent)}Separator: {self.separator_before}")
        lines.append(self.item.dump(indent))
        return "\n".join(lines)


class MoveLiteralNode(ASTNode):
    """A chess move in algebraic notation: e4, Nf3, Qxd5, O-O, etc."""

    def __init__(self, notation: str, line: int):
        super().__init__(line)
        self.notation = notation

    def dump(self, indent: int = 0) -> str:
        return f"{self._prefix(indent)}MoveLiteral: {self.notation}"


class LineBranchNode(ASTNode):
    """
    A variation branch inside a position block:
        line <move_literal> { <move_sequence> }
    """

    def __init__(self, move_lit: str, moves: list, line: int):
        super().__init__(line)
        self.move_lit = move_lit     # the branching move notation
        self.moves = moves           # list[ASTNode] — continuation moves

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}LineBranch: {self.move_lit}"]
        for mv in self.moves:
            lines.append(mv.dump(indent + 1))
        return "\n".join(lines)


class PremoveCallNode(ASTNode):
    """
    A call to a premove subprogram:
        <id>( [args] )
    Arguments are move literals or identifiers only (no nested calls).
    Separated by COMMA or DOUBLE_COMMA.
    """

    def __init__(self, name: str, args: list, line: int):
        super().__init__(line)
        self.name = name         # premove function name
        self.args = args         # list[MoveLiteralNode | IdentifierNode]

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}PremoveCall: {self.name}"]
        for arg in self.args:
            lines.append(arg.dump(indent + 1))
        return "\n".join(lines)


# =====================================================================
# Leaf Expressions / Terminals
# =====================================================================

class IdentifierNode(ASTNode):
    """A variable or reference name."""

    def __init__(self, name: str, line: int):
        super().__init__(line)
        self.name = name

    def dump(self, indent: int = 0) -> str:
        return f"{self._prefix(indent)}Identifier: {self.name}"


class StringLiteralNode(ASTNode):
    """A string constant, typically a FEN position string."""

    def __init__(self, value: str, line: int):
        super().__init__(line)
        self.value = value

    def dump(self, indent: int = 0) -> str:
        return f"{self._prefix(indent)}StringLiteral: {self.value}"


class ColorLiteralNode(ASTNode):
    """A color literal: white or black."""

    def __init__(self, value: str, line: int):
        super().__init__(line)
        self.value = value

    def dump(self, indent: int = 0) -> str:
        return f"{self._prefix(indent)}ColorLiteral: {self.value}"


class PieceLiteralNode(ASTNode):
    """An explicit piece value: W-king, B-Q, white-rook, etc."""

    def __init__(self, value: str, line: int):
        super().__init__(line)
        self.value = value

    def dump(self, indent: int = 0) -> str:
        return f"{self._prefix(indent)}PieceLiteral: {self.value}"


class SquareLiteralNode(ASTNode):
    """A board square coordinate: A1, E4, H8, etc."""

    def __init__(self, value: str, line: int):
        super().__init__(line)
        self.value = value

    def dump(self, indent: int = 0) -> str:
        return f"{self._prefix(indent)}SquareLiteral: {self.value}"


class ThisNode(ASTNode):
    """The 'this' keyword — refers to the current board state in a position block."""

    def __init__(self, line: int):
        super().__init__(line)

    def dump(self, indent: int = 0) -> str:
        return f"{self._prefix(indent)}This"


# =====================================================================
# Eval Expressions
# =====================================================================

class EvalCallNode(ASTNode):
    """Evaluation call: eval( <expression> )"""

    def __init__(self, expr, line: int):
        super().__init__(line)
        self.expr = expr         # expression being evaluated

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}EvalCall"]
        lines.append(self.expr.dump(indent + 1))
        return "\n".join(lines)


class EvalMethodCallNode(ASTNode):
    """
    Eval method call: eval.move( [args] )
    The method field is always "move" per the current grammar.
    """

    def __init__(self, method: str, args: list, line: int):
        super().__init__(line)
        self.method = method     # "move"
        self.args = args         # list[ASTNode] — argument expressions

    def dump(self, indent: int = 0) -> str:
        lines = [f"{self._prefix(indent)}EvalMethodCall: {self.method}"]
        for arg in self.args:
            lines.append(arg.dump(indent + 1))
        return "\n".join(lines)
