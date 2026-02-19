#!/usr/bin/env python3
"""
Test runner script for Claw2Cline project.
This script runs all tests and generates a markdown report.
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

def run_test(test_file: str) -> dict:
    """Run a single test file and return results."""
    print(f"Running {test_file}...")
    
    try:
        # Run with more verbose output to get individual test results
        result = subprocess.run([
            sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        # Parse output to get statistics
        output_lines = result.stdout.split('\n')
        stats_line = ""
        for line in output_lines:
            if 'passed, ' in line or 'failed, ' in line or 'errors in' in line:
                stats_line = line.strip()
                break
        
        # Extract individual test results with better parsing
        test_results = []
        failed_test_logs = {}
        
        i = 0
        while i < len(output_lines):
            line = output_lines[i]
            if '::' in line and ('PASSED' in line or 'FAILED' in line or 'SKIPPED' in line or 'ERROR' in line):
                # Extract test name and status
                if 'PASSED' in line:
                    status = 'PASSED'
                elif 'FAILED' in line:
                    status = 'FAILED'
                elif 'SKIPPED' in line:
                    status = 'SKIPPED'
                elif 'ERROR' in line:
                    status = 'ERROR'
                else:
                    i += 1
                    continue
                
                # Find the test function name
                parts = line.split()
                for part in parts:
                    if '::' in part and status in part:
                        test_name = part.replace(status, '').strip()
                        if test_name.startswith('::'):
                            test_name = test_name[2:]
                        break
                else:
                    test_name = line.strip()
                
                test_results.append({
                    'name': test_name,
                    'status': status
                })
                
                # If this is a failed test, collect the error message
                if status == 'FAILED':
                    # Look for the error message after this line
                    j = i + 1
                    error_lines = []
                    while j < len(output_lines) and j < i + 10:  # Look ahead up to 10 lines
                        err_line = output_lines[j].strip()
                        if err_line and not err_line.startswith('::'):
                            error_lines.append(err_line)
                        elif err_line.startswith('::'):  # Next test starts
                            break
                        j += 1
                    
                    if error_lines:
                        # Take the first meaningful error line
                        error_msg = ' '.join(error_lines[:3])  # First 3 lines max
                        failed_test_logs[test_name] = error_msg
            
            i += 1
        
        return {
            'file': test_file,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'stats': stats_line,
            'passed': result.returncode == 0,
            'test_results': test_results,
            'failed_logs': failed_test_logs
        }
    except Exception as e:
        return {
            'file': test_file,
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
            'stats': 'Error running test',
            'passed': False,
            'test_results': [],
            'failed_logs': {}
        }

def parse_stats(stats_line: str) -> tuple:
    """Parse pytest statistics from output."""
    passed = failed = skipped = errors = 0
    
    if 'passed' in stats_line:
        passed = int(stats_line.split(' passed')[0].split()[-1])
    if 'failed' in stats_line:
        failed = int(stats_line.split(' failed')[0].split()[-1])
    if 'skipped' in stats_line:
        skipped = int(stats_line.split(' skipped')[0].split()[-1])
    if 'errors' in stats_line:
        errors = int(stats_line.split(' errors')[0].split()[-1])
    
    return passed, failed, skipped, errors

def generate_markdown_report(results: list) -> str:
    """Generate markdown report from test results."""
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_errors = 0
    
    report = f"# Test Results Report\n\n"
    report += f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # Create table header
    report += "| Test File | Status | Passed | Failed | Skipped | Errors | Details |\n"
    report += "|-----------|--------|--------|--------|---------|--------|---------|\n"
    
    # Individual test results
    for result in results:
        passed, failed, skipped, errors = parse_stats(result['stats'])
        total_tests += (passed + failed + skipped + errors)
        total_passed += passed
        total_failed += failed
        total_skipped += skipped
        total_errors += errors
        
        status_emoji = "✅" if result['passed'] else "❌"
        status_text = "PASS" if result['passed'] else "FAIL"
        
        # Remove the path prefix from filename
        short_filename = result['file'].replace('/opt/tong/ws/git-repo/Claw2Cline/', '')
        
        report += f"| {short_filename} | {status_text} | {passed} | {failed} | {skipped} | {errors} | {result['stats']} |\n"
    
    report += "\n"
    
    # Detailed results section with individual test case tables
    for result in results:
        passed, failed, skipped, errors = parse_stats(result['stats'])
        short_filename = result['file'].replace('/opt/tong/ws/git-repo/Claw2Cline/', '')
        status_emoji = "✅" if result['passed'] else "❌"
        report += f"## {status_emoji} {short_filename}\n\n"
        report += f"- **Status:** {'PASS' if result['passed'] else 'FAIL'}\n"
        report += f"- **Details:** {result['stats']}\n\n"
        
        # Add table for individual test cases
        if result['test_results']:
            report += "### Test Cases:\n\n"
            report += "| Test Case | Status |\n"
            report += "|-----------|--------|\n"
            for test_case in result['test_results']:
                status_icon = "✅" if test_case['status'] in ['PASSED', 'SKIPPED'] else "❌"
                report += f"| {test_case['name']} | {status_icon} {test_case['status']} |\n"
            report += "\n"
        
        # Add detailed error information for failed tests
        if result['failed_logs']:
            report += "### Failed Test Details:\n\n"
            report += "| Test Case | Error Message |\n"
            report += "|-----------|---------------|\n"
            for test_name, error_msg in result['failed_logs'].items():
                # Escape any pipe characters in the error message
                safe_error_msg = error_msg.replace('|', '\\|')
                report += f"| {test_name} | {safe_error_msg} |\n"
            report += "\n"
        
        if result['stderr']:
            report += f"### Errors:\n```\n{result['stderr']}\n```\n\n"
        
        if failed > 0 or errors > 0:
            # Extract failed test details from stdout
            lines = result['stdout'].split('\n')
            in_failures = False
            failure_details = []
            
            for line in lines:
                if 'FAILURES' in line or 'ERRORS' in line:
                    in_failures = True
                    continue
                if in_failures and line.strip() and '=' in line and '_' in line:
                    failure_details.append(line.strip())
                elif in_failures and line.strip() == '' and len(failure_details) > 0:
                    break
                elif in_failures and '====' in line:
                    break
            
            if failure_details:
                report += "### Failed Tests:\n"
                for detail in failure_details[:10]:  # Limit to first 10 failures
                    report += f"- {detail}\n"
                report += "\n"
    
    # Summary
    report += f"## 📊 Summary\n\n"
    report += f"- **Total Tests:** {total_tests}\n"
    report += f"- **Passed:** {total_passed}\n"
    report += f"- **Failed:** {total_failed}\n"
    report += f"- **Skipped:** {total_skipped}\n"
    report += f"- **Errors:** {total_errors}\n"
    success_rate = (total_passed/total_tests*100) if total_tests > 0 else 0
    report += f"- **Success Rate:** {success_rate:.1f}%\n\n"
    
    if total_failed == 0 and total_errors == 0:
        report += "🎉 **All tests passed!**\n"
    else:
        report += "⚠️ **Some tests failed. Please check the details above.**\n"
    
    return report

def main():
    """Main function to run all tests."""
    test_dir = Path(__file__).parent.parent / "test"
    
    if not test_dir.exists():
        print(f"Test directory {test_dir} does not exist!")
        return 1
    
    # Find all test files
    test_files = list(test_dir.glob("**/test_*.py"))
    
    if not test_files:
        print("No test files found!")
        return 1
    
    print(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file.name}")
    
    print("\nRunning tests...\n")
    
    results = []
    for test_file in test_files:
        result = run_test(str(test_file))
        results.append(result)
    
    # Generate markdown report
    report = generate_markdown_report(results)
    
    # Save report
    # Create out directory if it doesn't exist
    out_dir = Path(__file__).parent.parent / "out"
    out_dir.mkdir(exist_ok=True)
    
    report_path = out_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nTest report generated: {report_path}")
    print(f"Total: {len(test_files)} test files run")
    
    # Print summary to console
    total_passed = sum(1 for r in results if r['passed'])
    print(f"Passed: {total_passed}/{len(results)} files")
    
    return 0 if all(r['passed'] for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())