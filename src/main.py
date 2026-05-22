"""
CLL (Chess Language) — Main entry point.

Usage:
    python main.py <filename.cll> [--dump-tokens] [--dump-ast] [--type-check] [--run]
"""

import sys
import argparse

from lexer import Lexer
from parser import Parser
from errors import CllError


def main():
    ap = argparse.ArgumentParser(description="CLL — Chess Language Compiler")
    ap.add_argument("file", help="Path to a .cll source file")
    ap.add_argument("--dump-tokens", action="store_true",
                    help="Print all tokens produced by the lexer")
    ap.add_argument("--dump-ast", action="store_true",
                    help="Parse and print the AST")
    ap.add_argument("--type-check", action="store_true",
                    help="Run the type checker after parsing")
    ap.add_argument("--run", action="store_true",
                    help="Run the interpreter after type-checking")
    args = ap.parse_args()

    # Read source file
    try:
        with open(args.file, "r") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found.", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error: Could not read file '{args.file}': {e}",
              file=sys.stderr)
        sys.exit(1)

    # Lex
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
    except CllError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    # --dump-tokens: print tokens and exit
    if args.dump_tokens:
        for token in tokens:
            print(f"{token.line:>3}: {token.type.name:<20} {token.lexeme!r}")
        return

    # Parse
    try:
        parser = Parser(tokens)
        ast = parser.parse()
    except CllError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    # --dump-ast: print AST and exit
    if args.dump_ast:
        print(ast.dump())
        return

    # --type-check: run type checker
    if args.type_check:
        from type_checker import TypeChecker
        try:
            TypeChecker().check(ast)
        except CllError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        print("Type check successful.")
        return

    # --run: type-check then interpret
    if args.run:
        from type_checker import TypeChecker
        from interpreter import Interpreter
        try:
            TypeChecker().check(ast)
        except CllError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        try:
            Interpreter().execute(ast)
        except CllError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        return

    # Default: type-check then interpret (same as --run)
    from type_checker import TypeChecker
    from interpreter import Interpreter
    try:
        TypeChecker().check(ast)
    except CllError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    try:
        Interpreter().execute(ast)
    except CllError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

