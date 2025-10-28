"""
Test runner for the WozapAuto onboarding process.

This module provides utilities for running comprehensive tests
and generating test reports for the onboarding system.
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

def run_onboarding_tests():
    """Run all onboarding-related tests."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
    django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Define test patterns for onboarding
    test_patterns = [
        'core.tests.test_onboarding',
        'core.tests.test_models',
        'core.tests.test_forms', 
        'core.tests.test_views',
        'business.tests.test_models',
        'business.tests.test_forms',
        'business.tests.test_views',
    ]
    
    failures = test_runner.run_tests(test_patterns)
    return failures

def run_specific_test_module(module_name):
    """Run tests for a specific module."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
    django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    failures = test_runner.run_tests([module_name])
    return failures

def run_all_tests():
    """Run all tests in the project."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
    django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    failures = test_runner.run_tests()
    return failures

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'onboarding':
            failures = run_onboarding_tests()
        elif sys.argv[1] == 'all':
            failures = run_all_tests()
        else:
            failures = run_specific_test_module(sys.argv[1])
    else:
        failures = run_onboarding_tests()
    
    if failures:
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)
