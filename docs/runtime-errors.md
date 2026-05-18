# ChessLineLang Runtime Error Specification

## Overview

Runtime errors occur after successful:

```txt
Lexing
→ Parsing
→ Type Checking
```

These errors are raised during interpreter execution.

All runtime errors derive from:

```python
RuntimeCllError
```

Example invalid runtime programs are located under:

```txt
interpreter-invalid/
```

---

# Runtime Error Hierarchy

```txt
RuntimeCllError
├── InvalidFENError
├── IllegalMoveError
├── IncompatiblePremoveError
├── IllegalBoardError
├── EmptySquareError
├── UninitializedVariableError
├── MissingEngineError
└── EngineEvaluationError
```

---

# General Runtime Semantics

ChessLineLang allows some semantically dangerous constructions to pass parsing and type checking.

Examples include:

- manually constructed illegal boards
- incompatible premove lines
- empty square accesses
- illegal chess moves

These are detected only during execution.

Reference runtime-invalid examples:

```txt
interpreter-invalid/
```

---

# Invalid FEN Error

## Description

Raised when a FEN string cannot be parsed into a valid chess position.

Reference examples:

```txt
interpreter-invalid/
```

---

# Illegal Move Error

## Description

Raised when a chess move cannot legally be played on the current board state.

Applies to:

- position blocks
- line branches
- move variables
- premove execution

Reference examples:

```txt
interpreter-invalid/
```

---

# Incompatible Premove Error

## Description

Raised when two premove sequences cannot be interleaved into one legal chess line.

This is a ChessLineLang-specific runtime semantic rule.

Reference examples:

```txt
interpreter-invalid/
```

---

# Illegal Board Error

## Description

Raised when a board position violates chess legality rules and is evaluated using:

```cll
eval(board)
eval.move(board)
```

Examples of illegal boards include:

- adjacent kings
- missing kings
- impossible side-to-move states

Illegal manually-created boards are allowed until evaluation is requested.

Reference examples:

```txt
interpreter-invalid/
```

---

# Empty Square Error

## Description

Raised when reading a square that contains no piece.

Reference examples:

```txt
interpreter-invalid/
```

---

# Uninitialized Variable Error

## Description

Raised when a declared variable is used before receiving a value.

Reference examples:

```txt
interpreter-invalid/
```

---

# Missing Engine Error

## Description

Raised when:

```cll
eval(board)
eval.move(board)
```

is called without a configured Stockfish engine.

Reference examples:

```txt
interpreter-invalid/
```

---

# Engine Evaluation Error

## Description

Raised when the external chess engine fails during evaluation.

Possible causes:

- engine crash
- communication failure
- invalid engine response

Reference examples:

```txt
interpreter-invalid/
```

---

# Position Block Semantics

## Line Branches

Line branches execute on copied board states.

Semantics:

1. Current board copied
2. Branch move applied to copy
3. Branch body executed on copy

Illegal branch moves raise:

```txt
IllegalMoveError
```

---

# Branch Assignment Semantics

Assignments inside line branches modify the normal runtime environment.

If multiple branches assign the same variable:

```txt
Later source-order assignment overwrites earlier assignment.
```

---

# Runtime Phase Pipeline

```txt
Source Code
    ↓
Lexer
    ↓
Parser
    ↓
AST
    ↓
Type Checker
    ↓
Interpreter
    ↓
Runtime Errors (if any)
```