# ChessLineLang Type Checker Specification

## Overview

ChessLineLang uses a static type checker executed after parsing and AST construction.

The parser accepts syntactically valid expressions broadly, while the type checker enforces semantic correctness and type compatibility.

ChessLineLang is strongly typed and does not support general implicit type coercion.

---

# Type System

## Primitive / Domain Types

```txt
BOARD
MOVE
PIECE
COLOR
SQUARE
STRING
EVAL_SCORE
MOVE_SEQUENCE
PREMOVE
VOID
```

---

# General Rules

## No Implicit Coercion

ChessLineLang does not automatically convert values between unrelated types.

Examples:

```cll
pc p <= pos.turn        // invalid
tr side <= pos.sq(E1)   // invalid
mv m <= eval(pos)       // invalid
```

The parser may accept these syntactically, but the type checker rejects them.

---

# Declarations

## Board Declarations

```cll
bd pos <= starting
bd pos <= empty
bd pos <= "FEN_STRING"
```

Type:

```txt
BOARD
```

Special rule:

A FEN string used in a board declaration is not considered a string-to-board coercion.
It is a dedicated board initialization construct.

---

## Color Declarations

```cll
tr side <= white
tr side <= pos.turn
```

Rule:

```txt
RHS must evaluate to COLOR
```

---

## Piece Declarations

```cll
pc king_piece <= W-king
pc king_piece <= pos.sq(E1)
```

Rule:

```txt
RHS must evaluate to PIECE
```

---

## Move Declarations

```cll
mv best <= e4
mv best <= eval.move(pos)
```

Rule:

```txt
RHS must evaluate to MOVE
```

---

## Premove Declarations

```cll
premove london() {
    d4,,Bf4,,e3,,Nf3
}
```

Type:

```txt
PREMOVE
```

---

# Assignments

## Simple Assignment

```cll
x <= expr
```

Rule:

```txt
Type(x) must equal Type(expr)
```

---

## Board Attribute Assignment

```cll
pos.turn <= white
pos.tr <= side
```

Rules:

```txt
LHS object must be BOARD
RHS must evaluate to COLOR
```

---

## Square Assignment

```cll
pos.sq(E1) <= W-king
pos.sq(H1) <= pos.sq(A1)
```

Rules:

```txt
LHS object must be BOARD
RHS must evaluate to PIECE
```

---

# Accessor Expressions

## Board Attribute Access

```cll
pos.turn
pos.tr
pos.color
pos.cl
```

Type:

```txt
COLOR
```

---

## Square Access

```cll
pos.sq(E1)
pos.square(D4)
```

Type:

```txt
PIECE
```

Reading an empty square is considered a runtime/domain error rather than a type error.

---

# Eval System

## Evaluation Call

```cll
eval(pos)
```

Rule:

```txt
Argument must evaluate to BOARD
```

Return type:

```txt
EVAL_SCORE
```

---

## Best Move Evaluation

```cll
eval.move(pos)
```

Rule:

```txt
Argument must evaluate to BOARD
```

Return type:

```txt
MOVE
```

---

# Premove Calls

## Valid Forms

```cll
london(kings_indian)

london(g6,,Bg7,,d6,,Nf6)
```

Arguments:

```txt
PREMOVE
or
ONE-SIDE MOVE SEQUENCE
```

Return type:

```txt
MOVE_SEQUENCE
```

---

# Special Assignment Rule

ChessLineLang contains one special semantic assignment rule:

```cll
pos <= london(g6,,Bg7)
```

Rule:

```txt
BOARD <= MOVE_SEQUENCE
```

This is not considered implicit coercion.
It is a dedicated language semantic rule representing application of a move sequence to a board.

---

# Print Rules

The following types are printable:

```txt
BOARD
MOVE
PIECE
COLOR
STRING
SQUARE
EVAL_SCORE
```

The following are not directly printable:

```txt
MOVE_SEQUENCE
PREMOVE
VOID
```

---

# this Keyword

```cll
this
```

Type:

```txt
BOARD
```

Usage restriction:

```txt
Valid only inside position blocks and line branches.
```

Example:

```cll
pos.{
    line e5 {
        saved <= this
    }
}
```

Using `this` outside a position block is a type error.

---

# Position Blocks

```cll
pos.{
    e4,
    Nf3
}
```

Rule:

```txt
Target object must be BOARD
```

---

# Line Branches

```cll
line e5 {
    Nf3
}
```

Rules:

```txt
Allowed only inside position blocks or other line branches.
Branch move must be MOVE.
```

---

# Scoping Rules

ChessLineLang uses lexical scoping.

Scopes exist for:

```txt
Global scope
Position block scope
Line branch scope
Premove body scope
```

Variables declared inside a scope are local to that scope.

---

# Redeclaration Rules

```txt
Redeclaration in the same scope -> type error
Shadowing in inner scopes -> allowed
```

Example:

```cll
pc p <= W-king

pos.{
    pc p <= B-king   // allowed shadowing
}
```

---

# Declaration Before Use

ChessLineLang requires declaration before use.

Example:

```cll
print(x)     // invalid
pc x <= W-king
```

---

# Type Checker Phase

The type checker operates after parsing:

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
Interpreter / Runtime
```

The parser validates syntax only.
The type checker validates semantic correctness and type compatibility.
