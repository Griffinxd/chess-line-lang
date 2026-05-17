"""
Recursive-descent parser for the CLL (Chess Language).

Consumes a list of Token objects from the lexer and produces
an AST rooted at a ProgramNode.
"""

from tokens import TokenType, Token
from ast_nodes import *
from errors import ParserError


class Parser:
    """
    Recursive-descent parser for CLL.

    Usage:
        parser = Parser(tokens)
        ast = parser.parse()
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def peek(self, offset: int = 0) -> Token:
        """Return the token at pos + offset without consuming it."""
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF

    def advance(self) -> Token:
        """Consume and return the current token, then move forward."""
        token = self.tokens[self.pos]
        if not self.at_end():
            self.pos += 1
        return token

    def at_end(self) -> bool:
        """True if the current token is EOF."""
        return self.peek().type == TokenType.EOF

    def check(self, *types: TokenType) -> bool:
        """True if the current token's type matches any of the given types."""
        if self.at_end():
            return False
        return self.peek().type in types

    def match(self, *types: TokenType) -> Token | None:
        """If the current token matches any type, consume and return it; else None."""
        if self.check(*types):
            return self.advance()
        return None

    def expect(self, token_type: TokenType, message: str) -> Token:
        """Consume the current token if it matches; otherwise raise ParserError."""
        if self.check(token_type):
            return self.advance()
        curr = self.peek()
        raise ParserError(
            f"{message} (got {curr.type.name} '{curr.lexeme}')",
            curr.line,
        )

    # ------------------------------------------------------------------
    # Top-level
    # ------------------------------------------------------------------

    def parse(self) -> ProgramNode:
        """<program> ::= { <statement> }"""
        line = self.peek().line
        statements = []
        while not self.at_end():
            statements.append(self.parse_statement())
        return ProgramNode(statements, line)

    # ------------------------------------------------------------------
    # Statement dispatcher
    # ------------------------------------------------------------------

    def parse_statement(self) -> ASTNode:
        """
        <statement> ::= <declaration>
                       | <assignment>
                       | <position_block>
                       | <print_stmt>
                       | <expression_stmt>

        Dispatches based on the current (and sometimes next) token.
        """

        # --- Keyword-led declarations ---
        if self.check(TokenType.BD, TokenType.BOARD):
            return self.parse_board_decl()

        if self.check(TokenType.TR, TokenType.TURN, TokenType.CL, TokenType.COLOR):
            return self.parse_color_decl()

        if self.check(TokenType.PC, TokenType.PIECE):
            return self.parse_piece_decl()

        if self.check(TokenType.MV, TokenType.MOVE):
            return self.parse_move_decl()

        if self.check(TokenType.PREMOVE):
            return self.parse_premove_decl()

        # --- print ---
        if self.check(TokenType.PRINT):
            return self.parse_print_stmt()

        # --- Identifier-led: requires lookahead to disambiguate ---
        if self.check(TokenType.IDENTIFIER):
            # id . { ... }  →  position block
            if (self.peek(1).type == TokenType.DOT
                    and self.peek(2).type == TokenType.LBRACE):
                return self.parse_position_block()

            # id <= ...  →  simple assignment
            if self.peek(1).type == TokenType.ASSIGN:
                return self.parse_assignment()

            # id . (tr|turn|cl|color) <=  →  board attribute assignment
            if self.peek(1).type == TokenType.DOT:
                next_type = self.peek(2).type
                if next_type in (TokenType.TR, TokenType.TURN,
                                 TokenType.CL, TokenType.COLOR):
                    return self.parse_assignment()

                # id . (sq|square) ( ...  →  square assignment
                if next_type in (TokenType.SQ, TokenType.SQUARE):
                    return self.parse_assignment()

        # --- Fallback: expression statement ---
        return self.parse_expression_stmt()

    # ------------------------------------------------------------------
    # Declaration stubs
    # ------------------------------------------------------------------

    def parse_board_decl(self) -> BoardDeclNode:
        """<board_decl> ::= ("bd" | "board") <identifier_list> [ ASSIGN <board_init> ]"""
        keyword = self.advance()  # consume bd / board
        line = keyword.line

        # <identifier_list> ::= <identifier> { COMMA <identifier> }
        names = [self.expect(TokenType.IDENTIFIER,
                             "Expected identifier after board keyword").lexeme]
        while self.match(TokenType.COMMA):
            names.append(self.expect(TokenType.IDENTIFIER,
                                     "Expected identifier after ','").lexeme)

        # optional  ASSIGN <board_init>
        init = None
        if self.match(TokenType.ASSIGN):
            init = self.parse_board_init()

        return BoardDeclNode(names, init, line)

    def parse_color_decl(self) -> ColorDeclNode:
        """<color_decl> ::= ("tr"|"turn"|"cl"|"color") <identifier> ASSIGN <expression>"""
        keyword = self.advance()  # consume tr / turn / cl / color
        line = keyword.line
        name = self.expect(TokenType.IDENTIFIER,
                           "Expected identifier after color keyword").lexeme
        self.expect(TokenType.ASSIGN, "Expected '<=' in color declaration")
        val = self.parse_expression()
        return ColorDeclNode(name, val, line)

    def parse_piece_decl(self) -> PieceDeclNode:
        """<piece_decl> ::= ("pc"|"piece") <identifier> ASSIGN <expression>"""
        keyword = self.advance()  # consume pc / piece
        line = keyword.line
        name = self.expect(TokenType.IDENTIFIER,
                           "Expected identifier after piece keyword").lexeme
        self.expect(TokenType.ASSIGN, "Expected '<=' in piece declaration")
        value = self.parse_expression()
        return PieceDeclNode(name, value, line)

    def parse_move_decl(self) -> MoveDeclNode:
        """<move_decl> ::= ("mv"|"move") <identifier> ASSIGN <expression>"""
        keyword = self.advance()  # consume mv / move
        line = keyword.line
        name = self.expect(TokenType.IDENTIFIER,
                           "Expected identifier after move keyword").lexeme
        self.expect(TokenType.ASSIGN, "Expected '<=' in move declaration")
        expr = self.parse_expression()
        return MoveDeclNode(name, expr, line)

    def parse_premove_decl(self) -> PremoveDeclNode:
        """
        <premove_decl> ::= PREMOVE IDENTIFIER
                           LPAREN RPAREN
                           LBRACE [ <premove_body> ] RBRACE
        <premove_body> ::= <move_literal> { DOUBLE_COMMA <move_literal> }
        """
        kw = self.advance()  # consume 'premove'
        line = kw.line
        name = self.expect(TokenType.IDENTIFIER,
                           "Expected identifier after 'premove'").lexeme

        self.expect(TokenType.LPAREN, "Expected '(' after premove name")
        self.expect(TokenType.RPAREN, "Expected ')' after '('")

        # --- premove body ---
        self.expect(TokenType.LBRACE, "Expected '{' for premove body")
        body = []
        if not self.check(TokenType.RBRACE):
            first_tok = self.expect(TokenType.MOVE_LITERAL, "Expected move literal in premove body")
            first_item = MoveLiteralNode(first_tok.lexeme, first_tok.line)
            body.append(PremoveItemNode(first_item, None, first_item.line))
            while self.check(TokenType.DOUBLE_COMMA):
                sep_tok = self.advance()  # consume ,,
                next_tok = self.expect(TokenType.MOVE_LITERAL, "Expected move literal after ',,'")
                next_item = MoveLiteralNode(next_tok.lexeme, next_tok.line)
                body.append(PremoveItemNode(next_item, "DOUBLE_COMMA", next_item.line))
        self.expect(TokenType.RBRACE, "Expected '}' after premove body")

        return PremoveDeclNode(name, body, line)

    # ------------------------------------------------------------------
    # Statement stubs
    # ------------------------------------------------------------------

    def parse_print_stmt(self) -> PrintStmtNode:
        """<print_stmt> ::= "print" LPAREN <expression> RPAREN"""
        kw = self.advance()  # consume 'print'
        line = kw.line
        self.expect(TokenType.LPAREN, "Expected '(' after 'print'")
        expr = self.parse_expression()
        self.expect(TokenType.RPAREN, "Expected ')' after print expression")
        return PrintStmtNode(expr, line)

    def parse_position_block(self) -> PositionBlockNode:
        """<position_block> ::= <identifier> DOT LBRACE [ <move_sequence> ] RBRACE"""
        id_tok = self.advance()  # consume board identifier
        line = id_tok.line
        self.expect(TokenType.DOT, "Expected '.' after board identifier")
        self.expect(TokenType.LBRACE, "Expected '{' for position block")

        moves = []
        if not self.check(TokenType.RBRACE):
            moves = self.parse_move_sequence()

        self.expect(TokenType.RBRACE, "Expected '}' after move sequence")
        return PositionBlockNode(id_tok.lexeme, moves, line)

    def parse_assignment(self) -> ASTNode:
        """
        <assignment> ::= <identifier> ASSIGN <expression>
                       | <board_attribute> ASSIGN <expression>
                       | <square_assignment>
        Dispatches based on lookahead after the identifier.
        """
        id_tok = self.advance()  # consume identifier
        line = id_tok.line

        # --- Form 1: id <= expr ---
        if self.check(TokenType.ASSIGN):
            self.advance()  # consume <=
            value = self.parse_expression()
            return AssignmentNode(
                IdentifierNode(id_tok.lexeme, line), value, line
            )

        # --- Forms 2 & 3: id . something ---
        if self.check(TokenType.DOT):
            self.advance()  # consume .

            # Form 2: id.tr/turn/cl/color <= expr  (board attribute)
            if self.check(TokenType.TR, TokenType.TURN,
                          TokenType.CL, TokenType.COLOR):
                attr_tok = self.advance()  # consume attribute keyword
                self.expect(TokenType.ASSIGN,
                            "Expected '<=' after board attribute")
                value = self.parse_expression()
                return AssignmentNode(
                    BoardAttributeNode(id_tok.lexeme, attr_tok.lexeme, line),
                    value, line,
                )

            # Form 3: id.sq/square(SQUARE_LITERAL) <= piece_value
            if self.check(TokenType.SQ, TokenType.SQUARE):
                self.advance()  # consume sq / square
                self.expect(TokenType.LPAREN, "Expected '(' after 'sq'")
                sq_tok = self.expect(TokenType.SQUARE_LITERAL,
                                     "Expected square coordinate (e.g. A1)")
                self.expect(TokenType.RPAREN, "Expected ')' after square")
                self.expect(TokenType.ASSIGN,
                            "Expected '<=' after square accessor")
                value = self.parse_expression()
                return SquareAssignmentNode(
                    id_tok.lexeme,
                    SquareLiteralNode(sq_tok.lexeme, sq_tok.line),
                    value, line,
                )

        curr = self.peek()
        raise ParserError(
            f"Invalid assignment form (got {curr.type.name} '{curr.lexeme}')",
            curr.line,
        )

    def parse_expression_stmt(self) -> ExpressionStmtNode:
        """<expression_stmt> ::= <expression>"""
        expr = self.parse_expression()
        return ExpressionStmtNode(expr, expr.line)

    # ------------------------------------------------------------------
    # Move-sequence stubs
    # ------------------------------------------------------------------

    def parse_move_sequence(self) -> list:
        """
        <move_sequence> ::= <move_item> { COMMA <move_item> }
        No trailing comma allowed. DOUBLE_COMMA not accepted here.
        """
        items = [self.parse_move_item()]
        while self.match(TokenType.COMMA):
            items.append(self.parse_move_item())
        return items

    def parse_move_item(self) -> ASTNode:
        """
        <move_item> ::= <declaration>
                      | <line_branch>
                      | <assignment>
                      | <print_stmt>
                      | <expression_stmt>
        Dispatches by lookahead.
        """
        # --- Keyword-led declarations ---
        if self.check(TokenType.BD, TokenType.BOARD):
            return self.parse_board_decl()

        if self.check(TokenType.TR, TokenType.TURN, TokenType.CL, TokenType.COLOR):
            return self.parse_color_decl()

        if self.check(TokenType.PC, TokenType.PIECE):
            return self.parse_piece_decl()

        if self.check(TokenType.MV, TokenType.MOVE):
            return self.parse_move_decl()

        if self.check(TokenType.PREMOVE):
            return self.parse_premove_decl()

        # LINE => line branch
        if self.check(TokenType.LINE):
            return self.parse_line_branch()

        # PRINT => print statement
        if self.check(TokenType.PRINT):
            return self.parse_print_stmt()

        # IDENTIFIER + lookahead (assignments)
        if self.check(TokenType.IDENTIFIER):
            if self.peek(1).type == TokenType.ASSIGN:
                return self.parse_assignment()
            if self.peek(1).type == TokenType.DOT:
                next_type = self.peek(2).type
                if next_type in (TokenType.TR, TokenType.TURN,
                                 TokenType.CL, TokenType.COLOR,
                                 TokenType.SQ, TokenType.SQUARE):
                    return self.parse_assignment()

        # Fallback => expression statement
        return self.parse_expression_stmt()

    def parse_line_branch(self) -> LineBranchNode:
        """<line_branch> ::= "line" <move_literal> LBRACE [ <move_sequence> ] RBRACE"""
        kw = self.advance()  # consume 'line'
        line = kw.line
        move_tok = self.expect(TokenType.MOVE_LITERAL,
                               "Expected move literal after 'line'")
        self.expect(TokenType.LBRACE, "Expected '{' for line branch")

        moves = []
        if not self.check(TokenType.RBRACE):
            moves = self.parse_move_sequence()

        self.expect(TokenType.RBRACE, "Expected '}' after line moves")
        return LineBranchNode(move_tok.lexeme, moves, line)

    def parse_premove_call(self) -> PremoveCallNode:
        """
        <premove_call> ::= <identifier> LPAREN <premove_arg> RPAREN
        <premove_arg> ::= <identifier> | <one_side_move_list>
        <one_side_move_list> ::= <move_literal> { DOUBLE_COMMA <move_literal> }
        """
        id_tok = self.advance()  # consume identifier (premove name)
        line = id_tok.line
        self.expect(TokenType.LPAREN, "Expected '(' after premove name")

        args = []
        if self.check(TokenType.IDENTIFIER):
            tok = self.advance()
            args.append(PremoveItemNode(IdentifierNode(tok.lexeme, tok.line), None, tok.line))
        elif self.check(TokenType.MOVE_LITERAL):
            tok = self.advance()
            args.append(PremoveItemNode(MoveLiteralNode(tok.lexeme, tok.line), None, tok.line))
            while self.check(TokenType.DOUBLE_COMMA):
                sep_tok = self.advance() # consume DOUBLE_COMMA
                move_tok = self.expect(TokenType.MOVE_LITERAL, "Expected move literal after ',,'")
                args.append(PremoveItemNode(MoveLiteralNode(move_tok.lexeme, move_tok.line), "DOUBLE_COMMA", move_tok.line))
        else:
            curr = self.peek()
            raise ParserError(
                f"Expected identifier or move literal in premove call "
                f"(got {curr.type.name} '{curr.lexeme}')",
                curr.line,
            )

        self.expect(TokenType.RPAREN, "Expected ')' after premove arguments")
        return PremoveCallNode(id_tok.lexeme, args, line)

    # ------------------------------------------------------------------
    # Expression stubs
    # ------------------------------------------------------------------

    def parse_expression(self) -> ASTNode:
        """
        <expression> ::= "this" | <eval_method_call> | <eval_call>
                       | <premove_call> | <string_literal> | <piece_value>
                       | <square_literal> | <move_literal> | <identifier>
        """
        # this
        if self.check(TokenType.THIS):
            tok = self.advance()
            return ThisNode(tok.line)

        # eval.method(...) or eval(...)
        if self.check(TokenType.EVAL):
            if self.peek(1).type == TokenType.DOT:
                return self.parse_eval_method_call()
            return self.parse_eval_call()

        # identifier — could be premove_call if followed by '('
        if self.check(TokenType.IDENTIFIER):
            if self.peek(1).type == TokenType.LPAREN:
                return self.parse_premove_call()
            # RHS board access expressions
            if self.peek(1).type == TokenType.DOT:
                next_type = self.peek(2).type
                if next_type in (TokenType.TR, TokenType.TURN, TokenType.CL, TokenType.COLOR):
                    id_tok = self.advance()
                    self.advance() # consume DOT
                    attr_tok = self.advance()
                    return BoardAttributeNode(id_tok.lexeme, attr_tok.lexeme, id_tok.line)
                if next_type in (TokenType.SQ, TokenType.SQUARE):
                    id_tok = self.advance()
                    self.advance() # consume DOT
                    self.advance() # consume sq/square
                    self.expect(TokenType.LPAREN, "Expected '(' after sq/square")
                    sq_tok = self.expect(TokenType.SQUARE_LITERAL, "Expected square coordinate (e.g. A1)")
                    self.expect(TokenType.RPAREN, "Expected ')' after square")
                    return SquareAccessNode(id_tok.lexeme, SquareLiteralNode(sq_tok.lexeme, sq_tok.line), id_tok.line)
            tok = self.advance()
            return IdentifierNode(tok.lexeme, tok.line)

        # string literal
        if self.check(TokenType.STRING_LITERAL):
            tok = self.advance()
            return StringLiteralNode(tok.lexeme, tok.line)

        # piece literal
        if self.check(TokenType.PIECE_LITERAL):
            tok = self.advance()
            return PieceLiteralNode(tok.lexeme, tok.line)

        # square literal
        if self.check(TokenType.SQUARE_LITERAL):
            tok = self.advance()
            return SquareLiteralNode(tok.lexeme, tok.line)

        # move literal
        if self.check(TokenType.MOVE_LITERAL):
            tok = self.advance()
            return MoveLiteralNode(tok.lexeme, tok.line)

        # color value (white/black) — used in board attribute assignments
        if self.check(TokenType.WHITE, TokenType.BLACK):
            tok = self.advance()
            return ColorLiteralNode(tok.lexeme, tok.line)

        curr = self.peek()
        raise ParserError(
            f"Unexpected token in expression: {curr.type.name} '{curr.lexeme}'",
            curr.line,
        )

    def parse_eval_call(self) -> EvalCallNode:
        """<eval_call> ::= "eval" LPAREN <expression> RPAREN"""
        kw = self.advance()  # consume 'eval'
        line = kw.line
        self.expect(TokenType.LPAREN, "Expected '(' after 'eval'")
        expr = self.parse_expression()
        self.expect(TokenType.RPAREN, "Expected ')' after eval expression")
        return EvalCallNode(expr, line)

    def parse_eval_method_call(self) -> EvalMethodCallNode:
        """
        <eval_method_call> ::= "eval" DOT "move"
                               LPAREN <expression> RPAREN
        """
        kw = self.advance()  # consume 'eval'
        line = kw.line
        self.expect(TokenType.DOT, "Expected '.' after 'eval'")
        self.expect(TokenType.MOVE, "Expected 'move' after 'eval.'")
        self.expect(TokenType.LPAREN, "Expected '(' after 'eval.move'")

        args = [self.parse_expression()]

        self.expect(TokenType.RPAREN, "Expected ')' after eval.move arguments")
        return EvalMethodCallNode("move", args, line)

    def parse_piece_value(self) -> ASTNode:
        """<piece_value> ::= <piece_literal> | <identifier>"""
        if self.check(TokenType.PIECE_LITERAL):
            tok = self.advance()
            return PieceLiteralNode(tok.lexeme, tok.line)
        if self.check(TokenType.IDENTIFIER):
            tok = self.advance()
            return IdentifierNode(tok.lexeme, tok.line)
        curr = self.peek()
        raise ParserError(
            f"Expected piece literal or identifier (got {curr.type.name} '{curr.lexeme}')",
            curr.line,
        )

    def parse_board_init(self) -> ASTNode:
        """<board_init> ::= "starting" | "empty" | <string_literal>"""
        if self.check(TokenType.STARTING, TokenType.EMPTY):
            tok = self.advance()
            return BoardInitNode(tok.lexeme, tok.line)

        if self.check(TokenType.STRING_LITERAL):
            tok = self.advance()
            return StringLiteralNode(tok.lexeme, tok.line)

        curr = self.peek()
        raise ParserError(
            f"Expected 'starting', 'empty', or FEN string "
            f"(got {curr.type.name} '{curr.lexeme}')",
            curr.line,
        )
