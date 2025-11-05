#!/usr/bin/env python3
"""
Performance test runner for SmartResume AI Resume Analyzer

This script provides a convenient way to run different types of performance tests
with proper configuration and result validation.

Requirements: 5.5, 6.6
"""
import os
import sys
import subprocess
import argparse
import json
import time
from typing import Dict, Any, List
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from tests.performance.config import get_test_config, validate_performance_requirements

class PerformanceTestRunner:
    """Manages execution of performance tests with different configurations"""
    
    def __init__(self, host: str = "http://localhost:8000"):
        self.host = host
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
    
    def run_test(self, test_type: str, locustfile: str = "locustfile.py", **kwargs) -> Dict[str, Any]:
        """
        Run a specific performance test
        
        Args:
            test_type: Type of test (load, stress, spike, endurance)
            locustfile: Locust file to use
            **kwargs: Additional configuration overrides
        
        Returns:
            Test results and validation status
        """
        config = get_test_config(test_type)
        config.update(kwargs)
        
        print(f"\n{'='*60}")
        print(f"RUNNING {test_type.upper()} TEST")
        print(f"{'='*60}")
        print(f"Description: {config['description']}")
        print(f"Users: {config['users']}")
        print(f"Spawn Rate: {config['spawn_rate']}/sec")
        print(f"Duration: {config['run_time']}")
        print(f"Host: {self.host}")
        print(f"{'='*60}")
        
        # Prepare locust command
        locust_file_path = Path(__file__).parent / locustfile
        
        cmd = [
            "locust",
            "-f", str(locust_file_path),
            "--host", self.host,
            "--users", str(config["users"]),
            "--spawn-rate", str(config["spawn_rate"]),
            "--run-time", config["run_time"],
            "--headless",
            "--print-stats",
            "--html", str(self.results_dir / f"{config['test_name']}_report.html"),
            "--csv", str(self.results_dir / f"{config['test_name']}")
        ]
        
        # Run the test
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
            end_time = time.time()
            
            # Parse results
            test_results = {
                "test_type": test_type,
                "config": config,
                "duration": end_time - start_time,
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Save results
            results_file = self.results_dir / f"{config['test_name']}_results.json"
            with open(results_file, 'w') as f:
                json.dump(test_results, f, indent=2)
            
            print(f"\nTest completed in {test_results['duration']:.2f} seconds")
            print(f"Results saved to: {results_file}")
            html_report_path = self.results_dir / f"{config['test_name']}_report.html"
            print(f"HTML report: {html_report_path}")
            
            return test_results
            
        except Exception as e:
            print(f"Error running test: {e}")
            return {
                "test_type": test_type,
                "config": config,
                "success": False,
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all performance test scenarios"""
        test_types = ["load", "stress", "spike"]  # Exclude endurance for quick runs
        results = []
        
        for test_type in test_types:
            result = self.run_test(test_type)
            results.append(result)
            
            # Brief pause between tests
            if test_type != test_types[-1]:
                print("\nWaiting 30 seconds before next test...")
                time.sleep(30)
        
        # Generate summary report
        self.generate_summary_report(results)
        return results
    
    def run_scenario_tests(self) -> Dict[str, Any]:
        """Run specialized scenario tests"""
        print(f"\n{'='*60}")
        print("RUNNING SCENARIO-BASED TESTS")
        print(f"{'='*60}")
        
        result = self.run_test(
            "scenario",
            locustfile="test_scenarios.py",
            users=50,
            spawn_rate=5,
            run_time="5m",
            test_name="scenario_test",
            description="Specialized scenario tests with different user types"
        )
        
        return result
    
    def generate_summary_report(self, results: List[Dict[str, Any]]):
        """Generate a summary report of all test results"""
        summary_file = self.results_dir / "test_summary.json"
        
        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(results),
            "successful_tests": sum(1 for r in results if r.get("success", False)),
            "failed_tests": sum(1 for r in results if not r.get("success", False)),
            "test_results": results
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Summary saved to: {summary_file}")
        print(f"{'='*60}")

def main():
    """Main entry point for performance test runner"""
    parser = argparse.ArgumentParser(description="Run SmartResume performance tests")
    parser.add_argument(
        "--host", 
        default="http://localhost:8000",
        help="Target host for testing (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--test-type",
        choices=["load", "stress", "spike", "endurance", "scenario", "all"],
        default="load",
        help="Type of test to run (default: load)"
    )
    parser.add_argument(
        "--users",
        type=int,
        help="Number of concurrent users (overrides config)"
    )
    parser.add_argument(
        "--spawn-rate",
        type=int,
        help="User spawn rate per second (overrides config)"
    )
    parser.add_argument(
        "--run-time",
        help="Test duration (e.g., '5m', '30s') (overrides config)"
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = PerformanceTestRunner(host=args.host)
    
    # Prepare configuration overrides
    overrides = {}
    if args.users:
        overrides["users"] = args.users
    if args.spawn_rate:
        overrides["spawn_rate"] = args.spawn_rate
    if args.run_time:
        overrides["run_time"] = args.run_time
    
    # Run tests based on type
    if args.test_type == "all":
        runner.run_all_tests()
    elif args.test_type == "scenario":
        runner.run_scenario_tests()
    else:
        runner.run_test(args.test_type, **overrides)

if __name__ == "__main__":
    main()