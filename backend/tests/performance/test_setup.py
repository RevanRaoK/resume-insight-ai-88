#!/usr/bin/env python3
"""
Setup verification test for performance testing

This script verifies that all performance testing components are properly
configured and can be executed.

Requirements: 5.5, 6.6
"""
import sys
import importlib
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import locust
        print(f"✅ Locust {locust.__version__} imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import locust: {e}")
        return False
    
    try:
        from locust import HttpUser, task, between, events
        print("✅ Locust components imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import locust components: {e}")
        return False
    
    try:
        import pandas as pd
        print(f"✅ Pandas {pd.__version__} imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import pandas: {e}")
        return False
    
    return True

def test_performance_modules():
    """Test that performance test modules can be imported"""
    print("\nTesting performance test modules...")
    
    modules_to_test = [
        "config",
        "locustfile", 
        "test_scenarios",
        "run_tests",
        "validate_requirements"
    ]
    
    for module_name in modules_to_test:
        try:
            spec = importlib.util.spec_from_file_location(
                module_name, 
                Path(__file__).parent / f"{module_name}.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"✅ {module_name}.py imported successfully")
        except Exception as e:
            print(f"❌ Failed to import {module_name}.py: {e}")
            return False
    
    return True

def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from config import get_test_config, ENDPOINT_THRESHOLDS
        
        # Test different config types
        config_types = ["load", "stress", "spike", "endurance"]
        for config_type in config_types:
            config = get_test_config(config_type)
            required_keys = ["users", "spawn_rate", "run_time", "test_name"]
            
            for key in required_keys:
                if key not in config:
                    print(f"❌ Missing key '{key}' in {config_type} config")
                    return False
            
            print(f"✅ {config_type} configuration valid")
        
        # Test endpoint thresholds
        if not ENDPOINT_THRESHOLDS:
            print("❌ ENDPOINT_THRESHOLDS is empty")
            return False
        
        print(f"✅ Endpoint thresholds configured for {len(ENDPOINT_THRESHOLDS)} endpoints")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_locust_files():
    """Test that locust files are syntactically correct"""
    print("\nTesting Locust file syntax...")
    
    locust_files = ["locustfile.py", "test_scenarios.py"]
    
    for file_name in locust_files:
        try:
            file_path = Path(__file__).parent / file_name
            with open(file_path, 'r') as f:
                code = f.read()
            
            compile(code, file_path, 'exec')
            print(f"✅ {file_name} syntax is valid")
            
        except SyntaxError as e:
            print(f"❌ Syntax error in {file_name}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error checking {file_name}: {e}")
            return False
    
    return True

def main():
    """Run all setup verification tests"""
    print("="*60)
    print("PERFORMANCE TEST SETUP VERIFICATION")
    print("="*60)
    
    tests = [
        ("Import Tests", test_imports),
        ("Module Tests", test_performance_modules),
        ("Configuration Tests", test_configuration),
        ("Syntax Tests", test_locust_files)
    ]
    
    all_passed = True
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if not test_func():
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Performance testing setup is ready!")
        print("\nNext steps:")
        print("1. Start the SmartResume backend application")
        print("2. Run: python validate_requirements.py")
        print("3. Or run: python run_tests.py --test-type load")
    else:
        print("❌ SOME TESTS FAILED - Please fix the issues above")
        return 1
    
    print("="*60)
    return 0

if __name__ == "__main__":
    sys.exit(main())