# Interpreter Implementation Batches

## Batch 1 — Runtime Foundation

Goal: create the interpreter skeleton without chess-specific complexity.

Tasks:
- Add `RuntimeCllError` to `errors.py`
- Create `src/interpreter.py`
- Add `Interpreter` class
- Add runtime environment dictionary
- Add `UNINITIALIZED` marker
- Implement variable declaration storage
- Implement identifier lookup
- Implement simple assignment
- Implement `print()`
- Add `--run` flag to `main.py`
- Update `run_runtime_tests.py` to actually call `Interpreter().execute(ast)`

Expected result:
- Programs can execute declarations, assignments, and prints.
- Uninitialized variable access raises `RuntimeCllError`.

---

## Batch 2 — Board Runtime Basics

Goal: support real board values using `python-chess`.

Tasks:
- Add `python-chess` dependency
- Implement board initialization:
  - `starting -> chess.Board()`
  - `empty -> chess.Board(None)`
  - FEN string -> `chess.Board(fen)`
- Invalid FEN raises `RuntimeCllError`
- Implement board assignment copy semantics
- Implement board printing
- Implement `pos.turn <= white/black`
- Implement board attribute read: `pos.turn`

Expected result:
- Board variables work.
- Invalid FEN runtime-invalid test passes.

---

## Batch 3 — Move Execution + Branching

Goal: make position blocks actually play chess moves.

Tasks:
- Implement position block execution: `pos.{ ... }`
- Implement move literal execution using `board.push_san()`
- Illegal move raises `RuntimeCllError`
- Implement `this`
- Implement `line <move> { ... }`
- Branches execute on copied board states
- Assignments inside branches update normal runtime environment
- Later branch assignment overwrites earlier assignment

Expected result:
- Illegal move test passes.
- Illegal branch test passes.
- `this` works correctly.

---

## Batch 4 — Square Access + Manual Board Editing

Goal: support piece placement and square reads.

Tasks:
- Implement piece literal conversion:
  - `W-king`, `B-Q`, etc. -> `chess.Piece`
- Implement square assignment:
  - `pos.sq(E1) <= W-king`
- Implement square access:
  - `pos.sq(E4)`
- Empty square access raises `RuntimeCllError`
- Implement basic illegal board detection before eval:
  - missing kings
  - adjacent kings
  - invalid board according to python-chess

Expected result:
- Empty square runtime test passes.
- Illegal manually-set board test reaches eval and fails correctly.

---

## Batch 5 — Premoves + Eval/Stockfish

Goal: finish domain-specific runtime features.

Tasks:
- Store premove declarations in a premove table
- Implement premove call expansion
- Interleave caller premove moves with argument premove moves
- Execute expanded move sequence on target board
- Incompatible premove raises `RuntimeCllError`
- Add `--stockfish PATH`
- Detect missing Stockfish
- `eval(pos)` raises missing engine if no engine configured
- `eval.move(pos)` raises missing engine if no engine configured
- Implement actual Stockfish evaluation
- Implement actual best-move lookup

Expected result:
- Incompatible premove test passes.
- Missing engine test passes.
- Final valid programs using eval work when Stockfish is configured.
