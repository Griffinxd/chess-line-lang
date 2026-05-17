"""
Type checker test runner for CLL.

- valid_*.cll      → must parse AND type-check successfully
- type-invalid/*.cll → must parse OK but fail type-check with TypeCheckError
"""

import os
import sys
import glob

# Add src to Python path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from lexer import Lexer
from parser import Parser
from type_checker import TypeChecker
from errors import CllError, TypeCheckError


def run_type_tests():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sample_dir = os.path.join(project_root, 'sample-programs')

    valid_files = sorted(glob.glob(os.path.join(sample_dir, 'valid_*.cll')))
    type_invalid_dir = os.path.join(sample_dir, 'type-invalid')
    type_invalid_files = sorted(glob.glob(os.path.join(type_invalid_dir, '*.cll')))

    passed = 0
    failed = 0

    if not valid_files:
        print("❌ No valid_*.cll files found.")
        failed += 1

    if not type_invalid_files:
        print("❌ No type-invalid/*.cll files found.")
        failed += 1

    # ------------------------------------------------------------------
    # Valid programs: must parse AND type-check
    # ------------------------------------------------------------------
    print("=== Testing Valid Programs (type check) ===")
    for fname in valid_files:
        basename = os.path.basename(fname)
        try:
            with open(fname, 'r') as f:
                source = f.read()
            tokens = Lexer(source).tokenize()
            ast = Parser(tokens).parse()
            TypeChecker().check(ast)
            print(f"✅ {basename} type-checked successfully.")
            passed += 1
        except Exception as e:
            print(f"❌ {basename} failed unexpectedly: {e}")
            failed += 1

    # ------------------------------------------------------------------
    # Type-invalid programs: must parse OK, then fail type-check
    # ------------------------------------------------------------------
    print("\n=== Testing Type-Invalid Programs ===")
    for fname in type_invalid_files:
        basename = os.path.basename(fname)
        try:
            with open(fname, 'r') as f:
                source = f.read()
            tokens = Lexer(source).tokenize()
            ast = Parser(tokens).parse()
        except CllError as e:
            # If it fails to parse, that is unexpected for type-invalid
            # programs (they should be parser-valid).
            print(f"❌ {basename} failed during parsing (expected parser-valid): {e}")
            failed += 1
            continue
        except Exception as e:
            print(f"❌ {basename} failed during parsing with unexpected error: {e}")
            failed += 1
            continue

        # Now run the type checker — expect TypeCheckError
        try:
            TypeChecker().check(ast)
            print(f"❌ {basename} type-checked successfully but was expected to fail!")
            failed += 1
        except TypeCheckError as e:
            print(f"✅ {basename} failed type-check as expected: {e}")
            passed += 1
        except Exception as e:
            print(f"❌ {basename} failed with unexpected exception (not TypeCheckError): {e}")
            failed += 1

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n=== Summary ===")
    total = len(valid_files) + len(type_invalid_files)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_type_tests()
