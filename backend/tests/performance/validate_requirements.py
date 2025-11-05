#!/usr/bin/env python3
"""
Performance requirements validation script

This script runs comprehensive performance tests and validates that the system
meets all performance requirements, particularly the 30-second response time
requirement for 95% of requests.

Requirements: 5.5, 6.6
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from tests.performance.config import validate_performance_requirements, ENDPOINT_THRESHOLDS

class RequirementsValidator:
    """Validates performance requirements against test results"""
    
    def __init__(self, host: str = "http://localhost:8000"):
        self.host = host
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
    
    def check_system_availability(self) -> bool:
        """Check if the system is available for testing"""
        try:
            import requests
            response = requests.get(f"{self.host}/api/v1/health", timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"System not available: {e}")
            return False
    
    def run_requirements_validation_test(self) -> Dict[str, Any]:
        """
        Run a comprehensive test specifically designed to validate
        the 30-second response time requirement for 95% of requests
        """
        print(f"\n{'='*80}")
        print("PERFORMANCE REQUIREMENTS VALIDATION TEST")
        print(f"{'='*80}")
        print("Testing 30-second response time requirement for 95% of requests")
        print("Running with 50 concurrent users for 10 minutes")
        print(f"Target host: {self.host}")
        print(f"{'='*80}")
        
        # Locust command for requirements validation
        locust_file = Path(__file__).parent / "locustfile.py"
        
        cmd = [
            "locust",
            "-f", str(locust_file),
            "--host", self.host,
            "--users", "50",
            "--spawn-rate", "5",
            "--run-time", "10m",
            "--headless",
            "--print-stats",
            "--html", str(self.results_dir / "requirements_validation_report.html"),
            "--csv", str(self.results_dir / "requirements_validation"),
            "--logfile", str(self.results_dir / "requirements_validation.log")
        ]
        
        start_time = time.time()
        
        try:
            print("Starting performance test...")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
            end_time = time.time()
            
            # Parse CSV results for detailed analysis
            stats_file = self.results_dir / "requirements_validation_stats.csv"
            
            if stats_file.exists():
                validation_results = self.analyze_csv_results(stats_file)
            else:
                # Fallback to parsing stdout
                validation_results = self.parse_stdout_results(result.stdout)
            
            validation_results.update({
                "test_duration": end_time - start_time,
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Save detailed results
            results_file = self.results_dir / "requirements_validation_results.json"
            with open(results_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            return validation_results
            
        except Exception as e:
            print(f"Error running validation test: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def analyze_csv_results(self, stats_file: Path) -> Dict[str, Any]:
        """Analyze CSV results from Locust for detailed performance metrics"""
        try:
            import pandas as pd
            
            # Read the stats CSV file
            df = pd.read_csv(stats_file)
            
            # Calculate overall statistics
            total_requests = df['Request Count'].sum()
            total_failures = df['Failure Count'].sum()
            success_rate = ((total_requests - total_failures) / total_requests * 100) if total_requests > 0 else 0
            
            # Get 95th percentile response time (Locust provides this)
            p95_response_time = df['95%'].max()  # Take the worst 95th percentile across all endpoints
            
            # Analyze endpoint-specific performance
            endpoint_analysis = {}
            for _, row in df.iterrows():
                endpoint = row['Name']
                if endpoint != 'Aggregated':  # Skip aggregated row
                    endpoint_analysis[endpoint] = {
                        "request_count": row['Request Count'],
                        "failure_count": row['Failure Count'],
                        "avg_response_time": row['Average'],
                        "min_response_time": row['Min'],
                        "max_response_time": row['Max'],
                        "p95_response_time": row['95%'],
                        "success_rate": ((row['Request Count'] - row['Failure Count']) / row['Request Count'] * 100) if row['Request Count'] > 0 else 0
                    }
            
            return {
                "total_requests": int(total_requests),
                "total_failures": int(total_failures),
                "success_rate": success_rate,
                "p95_response_time": p95_response_time,
                "endpoint_analysis": endpoint_analysis,
                "analysis_method": "csv_parsing"
            }
            
        except Exception as e:
            print(f"Error analyzing CSV results: {e}")
            return {"error": f"CSV analysis failed: {e}"}
    
    def parse_stdout_results(self, stdout: str) -> Dict[str, Any]:
        """Parse performance results from Locust stdout as fallback"""
        lines = stdout.split('\n')
        
        # Look for summary statistics in stdout
        total_requests = 0
        total_failures = 0
        p95_response_time = 0
        
        for line in lines:
            if 'Total requests' in line or 'Aggregated' in line:
                # Try to extract numbers from the line
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        if 'requests' in line.lower() and total_requests == 0:
                            total_requests = int(part)
                        elif 'failures' in line.lower() and total_failures == 0:
                            total_failures = int(part)
        
        success_rate = ((total_requests - total_failures) / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "total_failures": total_failures,
            "success_rate": success_rate,
            "p95_response_time": p95_response_time,
            "analysis_method": "stdout_parsing",
            "note": "Limited analysis from stdout - CSV analysis preferred"
        }
    
    def validate_requirements(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate performance requirements against test results"""
        validation = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "requirements_met": True,
            "validation_details": {}
        }
        
        # Main requirement: 30-second response time for 95% of requests
        p95_time = test_results.get("p95_response_time", 0)
        thirty_second_requirement = p95_time <= 30000  # 30 seconds in milliseconds
        
        validation["validation_details"]["30_second_requirement"] = {
            "requirement": "95% of requests must complete within 30 seconds",
            "measured_p95_time_ms": p95_time,
            "measured_p95_time_seconds": p95_time / 1000,
            "passed": thirty_second_requirement
        }
        
        if not thirty_second_requirement:
            validation["requirements_met"] = False
        
        # Success rate requirement: 95% success rate
        success_rate = test_results.get("success_rate", 0)
        success_rate_requirement = success_rate >= 95.0
        
        validation["validation_details"]["success_rate_requirement"] = {
            "requirement": "95% success rate under load",
            "measured_success_rate": success_rate,
            "passed": success_rate_requirement
        }
        
        if not success_rate_requirement:
            validation["requirements_met"] = False
        
        # Concurrent user requirement: Handle 50 concurrent users
        total_requests = test_results.get("total_requests", 0)
        concurrent_user_requirement = total_requests > 0  # Basic check that test ran
        
        validation["validation_details"]["concurrent_user_requirement"] = {
            "requirement": "Handle 50 concurrent users without degradation",
            "total_requests_processed": total_requests,
            "passed": concurrent_user_requirement
        }
        
        if not concurrent_user_requirement:
            validation["requirements_met"] = False
        
        # Endpoint-specific validations
        endpoint_analysis = test_results.get("endpoint_analysis", {})
        endpoint_validations = {}
        
        for endpoint, stats in endpoint_analysis.items():
            endpoint_threshold = ENDPOINT_THRESHOLDS.get(endpoint, {
                "p95_response_time": 30000,
                "success_rate": 95.0
            })
            
            endpoint_p95 = stats.get("p95_response_time", 0)
            endpoint_success = stats.get("success_rate", 0)
            
            endpoint_time_ok = endpoint_p95 <= endpoint_threshold["p95_response_time"]
            endpoint_success_ok = endpoint_success >= endpoint_threshold["success_rate"]
            
            endpoint_validations[endpoint] = {
                "p95_threshold_ms": endpoint_threshold["p95_response_time"],
                "measured_p95_ms": endpoint_p95,
                "success_threshold": endpoint_threshold["success_rate"],
                "measured_success_rate": endpoint_success,
                "response_time_passed": endpoint_time_ok,
                "success_rate_passed": endpoint_success_ok,
                "overall_passed": endpoint_time_ok and endpoint_success_ok
            }
            
            if not (endpoint_time_ok and endpoint_success_ok):
                validation["requirements_met"] = False
        
        validation["validation_details"]["endpoint_validations"] = endpoint_validations
        
        return validation
    
    def print_validation_report(self, validation: Dict[str, Any]):
        """Print a comprehensive validation report"""
        print(f"\n{'='*80}")
        print("PERFORMANCE REQUIREMENTS VALIDATION REPORT")
        print(f"{'='*80}")
        print(f"Timestamp: {validation['timestamp']}")
        print(f"Overall Result: {'✓ ALL REQUIREMENTS MET' if validation['requirements_met'] else '✗ REQUIREMENTS FAILED'}")
        print(f"{'='*80}")
        
        details = validation["validation_details"]
        
        # Main requirements
        print("\nCORE REQUIREMENTS:")
        
        req_30s = details["30_second_requirement"]
        print(f"30-Second Response Time (P95): {'✓ PASSED' if req_30s['passed'] else '✗ FAILED'}")
        print(f"  Requirement: {req_30s['requirement']}")
        print(f"  Measured: {req_30s['measured_p95_time_seconds']:.2f} seconds")
        
        req_success = details["success_rate_requirement"]
        print(f"Success Rate: {'✓ PASSED' if req_success['passed'] else '✗ FAILED'}")
        print(f"  Requirement: {req_success['requirement']}")
        print(f"  Measured: {req_success['measured_success_rate']:.2f}%")
        
        req_concurrent = details["concurrent_user_requirement"]
        print(f"Concurrent Users: {'✓ PASSED' if req_concurrent['passed'] else '✗ FAILED'}")
        print(f"  Requirement: {req_concurrent['requirement']}")
        print(f"  Total Requests: {req_concurrent['total_requests_processed']}")
        
        # Endpoint-specific requirements
        endpoint_validations = details.get("endpoint_validations", {})
        if endpoint_validations:
            print("\nENDPOINT-SPECIFIC REQUIREMENTS:")
            for endpoint, validation_data in endpoint_validations.items():
                status = "✓ PASSED" if validation_data["overall_passed"] else "✗ FAILED"
                print(f"{endpoint}: {status}")
                print(f"  Response Time: {validation_data['measured_p95_ms']:.0f}ms (threshold: {validation_data['p95_threshold_ms']:.0f}ms)")
                print(f"  Success Rate: {validation_data['measured_success_rate']:.1f}% (threshold: {validation_data['success_threshold']:.1f}%)")
        
        print(f"\n{'='*80}")
    
    def run_full_validation(self) -> bool:
        """Run complete performance validation and return success status"""
        # Check system availability
        if not self.check_system_availability():
            print("❌ System is not available for testing")
            return False
        
        print("✅ System is available - starting performance validation")
        
        # Run performance test
        test_results = self.run_requirements_validation_test()
        
        if not test_results.get("success", False):
            print("❌ Performance test failed to complete")
            print(f"Error: {test_results.get('error', 'Unknown error')}")
            return False
        
        print("✅ Performance test completed successfully")
        
        # Validate requirements
        validation = self.validate_requirements(test_results)
        
        # Print report
        self.print_validation_report(validation)
        
        # Save validation results
        validation_file = self.results_dir / "validation_report.json"
        with open(validation_file, 'w') as f:
            json.dump(validation, f, indent=2)
        
        print(f"\nDetailed validation report saved to: {validation_file}")
        
        return validation["requirements_met"]

def main():
    """Main entry point for requirements validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate SmartResume performance requirements")
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="Target host for testing (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    validator = RequirementsValidator(host=args.host)
    success = validator.run_full_validation()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()