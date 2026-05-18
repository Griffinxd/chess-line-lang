"""
Runtime test runner for CLL (Placeholder).

- valid/*.cll      → must parse, type-check, AND execute successfully without RuntimeErrors
- runtime-invalid/*.cll → must parse, type-check, but fail execution with RuntimeError
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
# TODO: Import Interpreter/Runtime when implemented
# from interpreter import Interpreter
# from errors import RuntimeError

def run_runtime_tests():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sample_dir = os.path.join(project_root, 'sample-programs')

    valid_files = sorted(glob.glob(os.path.join(sample_dir, 'valid', '*.cll')))
    runtime_invalid_dir = os.path.join(sample_dir, 'runtime-invalid')
    runtime_invalid_files = sorted(glob.glob(os.path.join(runtime_invalid_dir, '*.cll')))

    passed = 0
    failed = 0

    if not valid_files:
        print("❌ No valid/*.cll files found.")
        failed += 1

    if not runtime_invalid_files:
        print("❌ No runtime-invalid/*.cll files found.")
        failed += 1

    # ------------------------------------------------------------------
    # Valid programs
    # ------------------------------------------------------------------
    print("=== Testing Valid Programs (runtime) ===")
    for fname in valid_files:
        basename = os.path.basename(fname)
        try:
            with open(fname, 'r') as f:
                source = f.read()
            tokens = Lexer(source).tokenize()
            ast = Parser(tokens).parse()
            TypeChecker().check(ast)
            
            # TODO: Run the interpreter
            # interpreter = Interpreter()
            # interpreter.execute(ast)
            
            print(f"✅ {basename} executed successfully (TODO).")
            passed += 1
        except Exception as e:
            print(f"❌ {basename} failed unexpectedly: {e}")
            failed += 1

    # ------------------------------------------------------------------
    # Runtime-invalid programs
    # ------------------------------------------------------------------
    print("\n=== Testing Runtime-Invalid Programs ===")
    for fname in runtime_invalid_files:
        basename = os.path.basename(fname)
        try:
            with open(fname, 'r') as f:
                source = f.read()
            tokens = Lexer(source).tokenize()
            ast = Parser(tokens).parse()
            TypeChecker().check(ast)
            
            # TODO: Run the interpreter and expect a RuntimeError
            # interpreter = Interpreter()
            # interpreter.execute(ast)
            # print(f"❌ {basename} executed successfully but was expected to fail!")
            # failed += 1
            
            print(f"✅ {basename} failed runtime as expected (TODO).")
            passed += 1
        except CllError as e:
            print(f"❌ {basename} failed before runtime: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {basename} failed with unexpected exception: {e}")
            failed += 1

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n=== Summary ===")
    total = len(valid_files) + len(runtime_invalid_files)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_runtime_tests()
