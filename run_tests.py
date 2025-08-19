"""
Test runner for the web image converter application
Run all unit tests and generate a coverage report
"""
import unittest
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def discover_and_run_tests():
    """Discover and run all tests in the tests directory"""
    # Discover all test files in the tests directory
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(
        start_dir='tests',
        pattern='test_*.py',
        top_level_dir=str(project_root)
    )
    
    # Run the tests with verbose output
    test_runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = test_runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    # Return True if all tests passed
    return len(result.failures) == 0 and len(result.errors) == 0

def run_specific_test_module(module_name):
    """Run tests from a specific module"""
    try:
        test_loader = unittest.TestLoader()
        test_suite = test_loader.loadTestsFromName(f'tests.{module_name}')
        test_runner = unittest.TextTestRunner(verbosity=2)
        result = test_runner.run(test_suite)
        return len(result.failures) == 0 and len(result.errors) == 0
    except ImportError as e:
        print(f"Could not import test module '{module_name}': {e}")
        return False

if __name__ == "__main__":
    print("Web Image Converter - Test Suite")
    print("="*50)
    
    if len(sys.argv) > 1:
        # Run specific test module
        module_name = sys.argv[1]
        print(f"Running tests for module: {module_name}")
        success = run_specific_test_module(module_name)
    else:
        # Run all tests
        print("Running all tests...")
        success = discover_and_run_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
