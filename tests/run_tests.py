import os
import sys
import glob

# Add src to Python path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from lexer import Lexer
from parser import Parser
from errors import CllError


def run_tests():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sample_dir = os.path.join(project_root, 'sample-programs')

    valid_files = sorted(glob.glob(os.path.join(sample_dir, 'valid_*.cll')))
    invalid_files = sorted(glob.glob(os.path.join(sample_dir, 'invalid_*.cll')))

    passed = 0
    failed = 0

    if not valid_files:
        print("❌ No valid_*.cll files found.")
        failed += 1

    if not invalid_files:
        print("❌ No invalid_*.cll files found.")
        failed += 1
    

    print("=== Testing Valid Programs ===")
    for fname in valid_files:
        basename = os.path.basename(fname)
        try:
            with open(fname, 'r') as f:
                source = f.read()
            tokens = Lexer(source).tokenize()
            ast = Parser(tokens).parse()
            ast.dump()  # Ensure dump works without crashing
            print(f"✅ {basename} parsed successfully.")
            passed += 1
        except Exception as e:
            print(f"❌ {basename} failed unexpectedly: {e}")
            failed += 1

    print("\n=== Testing Invalid Programs ===")
    for fname in invalid_files:
        basename = os.path.basename(fname)
        try:
            with open(fname, 'r') as f:
                source = f.read()
            tokens = Lexer(source).tokenize()
            Parser(tokens).parse()
            print(f"❌ {basename} parsed successfully but was expected to fail!")
            failed += 1
        except CllError as e:
            print(f"✅ {basename} failed as expected: {e}")
            passed += 1
        except Exception as e:
            print(f"❌ {basename} failed with an unexpected exception (not CllError): {e}")
            failed += 1

    print("\n=== Summary ===")
    total = len(valid_files) + len(invalid_files)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
