## Lexical Structure

The lexical analyzer recognizes the following token categories:

| Token Category      | Description / Keywords | Pattern / Regular Expression |
|---------------------|------------------------|------------------------------|
| **KEYWORDS** | `bd`, `board`, `mv`, `move`, `sq`, `square`, `tr`, `turn`, `cl`, `color`, `pc`, `piece`, `empty`, `white`, `black`, `WHITE`, `BLACK`, `line`, `print`, `eval`, `this`, `starting`, `premove` | `bd\|board\|mv\|move\|sq\|square\|tr\|turn\|cl\|color\|pc\|piece\|empty\|white\|black\|WHITE\|BLACK\|line\|print\|eval\|this\|starting\|premove` |
| **IDENTIFIER** | Variable and function names | `[a-zA-Z_][a-zA-Z0-9_]*` |
| **MOVE_LITERAL** | Chess move notation (`e4`, `Nf3`, `Qxd5`, `cxd5`, `O-O`) | `\b(O-O-O\|O-O\|[a-h]x[a-h][1-8]\|[KQRBN]?[1-8]?[a-h][1-8](x?[a-h][1-8])?)([+#=!?])?\b` |
| **SQUARE_LITERAL** | Chess board square coordinates (`A1`, `D5`) | `[A-H][1-8]` |
| **PIECE_LITERAL** | Piece values with explicit color (`W-king`, `B-Q`, `white-rook`) | `(white\|black\|WHITE\|BLACK\|W\|B)-(king\|queen\|rook\|bishop\|knight\|pawn\|K\|Q\|R\|B\|N\|P)` |
| **STRING_LITERAL** | String / FEN notation literals | `"(\\.|[^"\\])*"` |
| **ASSIGN** | Assignment operator | `<=` |
| **DOT** | Member / block access operator | `\.` |
| **DOUBLE_COMMA** | Single-side move separator in premoves | `,,` |
| **COMMA** | Standard move separator | `,` |
| **LBRACE** | Left brace | `\{` |
| **RBRACE** | Right brace | `\}` |
| **LPAREN** | Left parenthesis | `\(` |
| **RPAREN** | Right parenthesis | `\)` |
| **COMMENT** | Single-line comments | `//.*` |
| **WHITESPACE** | Ignored whitespace | `[ \t\r\n]+` |
