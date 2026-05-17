## Current Status
This repository currently implements Part 1 of the compiler project, encompassing the frontend architecture (lexer, parser, and AST generation). Interpreter execution and runtime semantics are planned for Part 2.
# ChessLineLang (CLL)

## Project Overview
ChessLineLang (CLL) is a domain-specific language designed for chess opening preparation, line analysis, and puzzle description. It provides a formal syntax to define chess positions, execute sequences of moves, and request positional evaluations.

## Features
- Custom handwritten lexer tailored for chess notation and language constructs
- Handwritten recursive-descent parser
- Comprehensive Abstract Syntax Tree (AST) generation
- Strict syntax validation with line-level error reporting

## Project Structure
```text
.
├── docs/
│   └── grammar.txt
├── sample-programs/
│   ├── invalid_*.cll
│   └── valid_*.cll
├── src/
│   ├── ast_nodes.py
│   ├── errors.py
│   ├── lexer.py
│   ├── main.py
│   ├── parser.py
│   └── tokens.py
└── tests/
    └── run_tests.py
```

## Requirements
- Python 3.x

## Running the Project

```bash
python src/main.py sample-programs/valid_1.cll
python src/main.py sample-programs/valid_1.cll --dump-tokens
python src/main.py sample-programs/valid_1.cll --dump-ast
python tests/run_tests.py
```

