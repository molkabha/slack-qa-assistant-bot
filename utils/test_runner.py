import subprocess
import json
import os
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

class TestRunner:
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.running_tests = set()
    
    def run_pytest_tests(self, test_path: str, test_type: str, markers: List[str] = None, parallel: bool = False) -> Dict:
        if test_type in self.running_tests:
            return {"error": f"{test_type} tests are already running", "status": "running"}
        
        self.running_tests.add(test_type)
        
        try:
            allure_dir = f"reports/allure-results-{test_type}"
            results_file = f"reports/{test_type}_results.json"
            report_dir = f"reports/allure-report-{test_type}"
            
            Path(allure_dir).mkdir(exist_ok=True)
            Path(report_dir).mkdir(exist_ok=True)
            
            cmd = [
                "pytest", test_path,
                f"--alluredir={allure_dir}",
                "--json-report",
                f"--json-report-file={results_file}",
                "-v",
                "--tb=short"
            ]
            
            if markers:
                for marker in markers:
                    cmd.extend(["-m", marker])
            
            if parallel:
                import multiprocessing
                cpu_count = multiprocessing.cpu_count()
                cmd.extend(["-n", str(min(cpu_count, 4))])
            
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path.cwd())
            
            self.logger.info(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=1800
            )
            
            self.logger.info(f"Test execution completed with return code: {result.returncode}")
            self.logger.info(f"STDOUT: {result.stdout}")
            if result.stderr:
                self.logger.error(f"STDERR: {result.stderr}")
            
            self._generate_allure_report(allure_dir, report_dir)
            
            return self._parse_test_results(results_file, test_type)
            
        except subprocess.TimeoutExpired:
            return {"error": "Test execution timed out", "status": "timeout"}
        except Exception as e:
            self.logger.error(f"Error running tests: {str(e)}")
            return {"error": str(e), "status": "error"}
        finally:
            self.running_tests.discard(test_type)
    
    def run_api_tests(self, suite: str = None, markers: List[str] = None) -> Dict:
        if suite:
            test_path = f"tests/api/test_{suite}.py"
        else:
            test_path = "tests/test_api.py"
        
        return self.run_pytest_tests(test_path, "api", markers)
    
    def run_ui_tests(self, suite: str = None, markers: List[str] = None, headless: bool = True) -> Dict:
        if suite:
            test_path = f"tests/ui/test_{suite}.py"
        else:
            test_path = "tests/test_ui.py"
        
        if headless:
            os.environ["HEADLESS"] = "true"
        
        return self.run_pytest_tests(test_path, "ui", markers)
    
    def run_security_tests(self, suite: str = None) -> Dict:
        if suite:
            test_path = f"tests/security/test_{suite}.py"
        else:
            test_path = "tests/test_security.py"
        
        return self.run_pytest_tests(test_path, "security", ["security"])
    
    def run_performance_tests(self, suite: str = None) -> Dict:
        if suite:
            test_path = f"tests/performance/test_{suite}.py"
        else:
            test_path = "tests/test_performance.py"
        
        return self.run_pytest_tests(test_path, "performance", ["performance"])
    
    def run_smoke_tests(self) -> Dict:
        return self.run_pytest_tests("tests/", "smoke", ["smoke"])
    
    def run_regression_tests(self) -> Dict:
        return self.run_pytest_tests("tests/", "regression", ["regression"])
    
    def run_custom_command(self, command: List[str], test_type: str) -> Dict:
        if test_type in self.running_tests:
            return {"error": f"{test_type} tests are already running", "status": "running"}
        
        self.running_tests.add(test_type)
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            return {
                "command": " ".join(command),
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "status": "completed"
            }
            
        except subprocess.TimeoutExpired:
            return {"error": "Command execution timed out", "status": "timeout"}
        except Exception as e:
            return {"error": str(e), "status": "error"}
        finally:
            self.running_tests.discard(test_type)
    
    def run_newman_collection(self, collection_path: str, environment: str = None) -> Dict:
        if not Path(collection_path).exists():
            return {"error": f"Collection file not found: {collection_path}", "status": "error"}
        
        cmd = ["newman", "run", collection_path, "--reporters", "json", "--reporter-json-export", "reports/newman_results.json"]
        
        if environment:
            cmd.extend(["--environment", environment])
        
        return self.run_custom_command(cmd, "newman")
    
    def _generate_allure_report(self, allure_dir: str, report_dir: str):
        try:
            cmd = [
                "allure", "generate",
                allure_dir,
                "-o", report_dir,
                "--clean"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to generate Allure report: {result.stderr}")
            else:
                self.logger.info(f"Allure report generated successfully in {report_dir}")
                
        except Exception as e:
            self.logger.error(f"Error generating Allure report: {str(e)}")
    
    def _parse_test_results(self, results_file: str, test_type: str) -> Dict:
        try:
            if not Path(results_file).exists():
                return {
                    "error": "Results file not found",
                    "status": "error",
                    "test_type": test_type
                }
            
            with open(results_file, 'r') as f:
                data = json.load(f)
            
            summary = data.get('summary', {})
            
            return {
                "test_type": test_type,
                "total": summary.get('total', 0),
                "passed": summary.get('passed', 0),
                "failed": summary.get('failed', 0),
                "skipped": summary.get('skipped', 0),
                "error": summary.get('error', 0),
                "duration": data.get('duration', 0),
                "start_time": data.get('created', datetime.now().isoformat()),
                "status": "completed",
                "report_url": f"/allure-report-{test_type}",
                "success_rate": (summary.get('passed', 0) / summary.get('total', 1)) * 100
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing test results: {str(e)}")
            return {
                "error": f"Failed to parse results: {str(e)}",
                "status": "error",
                "test_type": test_type
            }
    
    def get_test_status(self, test_type: str) -> Dict:
        if test_type in self.running_tests:
            return {"status": "running", "test_type": test_type}
        
        results_file = f"reports/{test_type}_results.json"
        
        if Path(results_file).exists():
            return self._parse_test_results(results_file, test_type)
        
        return {"status": "not_run", "test_type": test_type}
    
    def stop_running_tests(self, test_type: str = None):
        if test_type:
            self.running_tests.discard(test_type)
        else:
            self.running_tests.clear()
    
    def cleanup_old_reports(self, days: int = 7):
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for report_dir in self.reports_dir.iterdir():
            if report_dir.is_dir() and report_dir.stat().st_mtime < cutoff_time:
                try:
                    import shutil
                    shutil.rmtree(report_dir)
                    self.logger.info(f"Cleaned up old report directory: {report_dir}")
                except Exception as e:
                    self.logger.error(f"Failed to clean up {report_dir}: {str(e)}")
    
    def generate_summary_report(self) -> Dict:
        summary = {
            "timestamp": datetime.now().isoformat(),
            "test_suites": {},
            "overall": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0
            }
        }
        
        for results_file in self.reports_dir.glob("*_results.json"):
            test_type = results_file.stem.replace("_results", "")
            results = self._parse_test_results(str(results_file), test_type)
            
            if results.get("status") == "completed":
                summary["test_suites"][test_type] = results
                summary["overall"]["total"] += results.get("total", 0)
                summary["overall"]["passed"] += results.get("passed", 0)
                summary["overall"]["failed"] += results.get("failed", 0)
                summary["overall"]["skipped"] += results.get("skipped", 0)
                summary["overall"]["duration"] += results.get("duration", 0)
        
        if summary["overall"]["total"] > 0:
            summary["overall"]["success_rate"] = (
                summary["overall"]["passed"] / summary["overall"]["total"]
            ) * 100
        else:
            summary["overall"]["success_rate"] = 0
        
        return summary

class ContinuousTestRunner:
    def __init__(self, test_runner: TestRunner, interval: int = 3600):
        self.test_runner = test_runner
        self.interval = interval
        self.running = False
        self.thread = None
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_continuous_tests)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("Continuous test runner started")
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.logger.info("Continuous test runner stopped")
    
    def _run_continuous_tests(self):
        while self.running:
            try:
                self.logger.info("Running scheduled tests")
                
                api_results = self.test_runner.run_smoke_tests()
                self.logger.info(f"Smoke tests completed: {api_results}")
                
                time.sleep(self.interval)
                
            except Exception as e:
                self.logger.error(f"Error in continuous test runner: {str(e)}")
                time.sleep(60)