"""
Runner to execute all CLL tests sequentially.
"""

import sys
import subprocess
import os

def run_tests(script_name):
    print(f"\n{'='*50}\nRunning {script_name}\n{'='*50}")
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    result = subprocess.run([sys.executable, script_path])
    if result.returncode != 0:
        print(f"\n❌ {script_name} failed!")
        return False
    return True

def main():
    scripts = [
        "run_parser_tests.py",
        "run_type_tests.py",
        "run_runtime_tests.py"
    ]
    
    all_passed = True
    for script in scripts:
        if not run_tests(script):
            all_passed = False
            break

    if all_passed:
        print(f"\n{'='*50}\n✅ All test suites passed successfully!\n{'='*50}")
        sys.exit(0)
    else:
        print(f"\n{'='*50}\n❌ Some tests failed. Check the output above.\n{'='*50}")
        sys.exit(1)

if __name__ == "__main__":
    main()
