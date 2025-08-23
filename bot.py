import os
import subprocess
import json
import asyncio
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from datetime import datetime
import requests
import time
import threading
from pathlib import Path
import schedule

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

class TestRunner:
    def __init__(self):
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    def run_api_tests(self):
        try:
            cmd = [
                "pytest", 
                "tests/test_api.py", 
                "--alluredir=reports/allure-results",
                "--json-report", 
                "--json-report-file=reports/test_results.json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            subprocess.run([
                "allure", "generate", 
                "reports/allure-results", 
                "-o", "reports/allure-report", 
                "--clean"
            ])
            
            return self._parse_test_results("reports/test_results.json")
            
        except Exception as e:
            return {"error": str(e), "passed": 0, "failed": 0, "total": 0}
    
    def run_ui_tests(self):
        try:
            cmd = [
                "pytest", 
                "tests/test_ui.py", 
                "--alluredir=reports/allure-results-ui",
                "--json-report", 
                "--json-report-file=reports/ui_results.json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            subprocess.run([
                "allure", "generate", 
                "reports/allure-results-ui", 
                "-o", "reports/allure-report-ui", 
                "--clean"
            ])
            
            return self._parse_test_results("reports/ui_results.json")
            
        except Exception as e:
            return {"error": str(e), "passed": 0, "failed": 0, "total": 0}
    
    def _parse_test_results(self, results_file):
        try:
            with open(results_file, 'r') as f:
                data = json.load(f)
            
            summary = data.get('summary', {})
            return {
                "total": summary.get('total', 0),
                "passed": summary.get('passed', 0),
                "failed": summary.get('failed', 0),
                "skipped": summary.get('skipped', 0),
                "duration": data.get('duration', 0)
            }
        except Exception:
            return {"error": "Failed to parse results", "passed": 0, "failed": 0, "total": 0}

class APIMonitor:
    def __init__(self, endpoints):
        self.endpoints = endpoints
        self.alert_channel = os.environ.get("ALERT_CHANNEL", "#qa-alerts")
    
    def check_endpoints(self):
        for endpoint in self.endpoints:
            try:
                start_time = time.time()
                response = requests.get(endpoint['url'], timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code != endpoint.get('expected_status', 200):
                    self._send_alert(endpoint['name'], endpoint['url'], 
                                   f"Status: {response.status_code}")
                
                if response_time > endpoint.get('max_response_time', 5000):
                    self._send_alert(endpoint['name'], endpoint['url'], 
                                   f"Slow response: {response_time:.2f}ms")
                
            except requests.exceptions.RequestException as e:
                self._send_alert(endpoint['name'], endpoint['url'], str(e))
    
    def _send_alert(self, name, url, error):
        message = f"API Health Alert\nEndpoint: {name}\nURL: {url}\nIssue: {error}"
        try:
            client.chat_postMessage(channel=self.alert_channel, text=message)
        except SlackApiError:
            pass

test_runner = TestRunner()

api_endpoints = [
    {"name": "Auth API", "url": "https://api.example.com/auth", "expected_status": 200},
    {"name": "Users API", "url": "https://api.example.com/users", "expected_status": 200},
    {"name": "Health Check", "url": "https://api.example.com/health", "expected_status": 200}
]

monitor = APIMonitor(api_endpoints)

@app.command("/run-tests")
def handle_run_tests(ack, say, command):
    ack()
    
    test_type = command['text'].strip().lower()
    
    if test_type == "api":
        say("Running API tests...")
        results = test_runner.run_api_tests()
        
        if "error" in results:
            say(f"Test execution failed: {results['error']}")
        else:
            message = f"API Test Results:\n"
            message += f"Total: {results['total']}\n"
            message += f"Passed: {results['passed']}\n"
            message += f"Failed: {results['failed']}\n"
            message += f"Duration: {results['duration']:.2f}s\n"
            message += f"Report: http://localhost:8080/allure-report"
            say(message)
    
    elif test_type == "ui":
        say("Running UI tests...")
        results = test_runner.run_ui_tests()
        
        if "error" in results:
            say(f"Test execution failed: {results['error']}")
        else:
            message = f"UI Test Results:\n"
            message += f"Total: {results['total']}\n"
            message += f"Passed: {results['passed']}\n"
            message += f"Failed: {results['failed']}\n"
            message += f"Duration: {results['duration']:.2f}s\n"
            message += f"Report: http://localhost:8080/allure-report-ui"
            say(message)
    
    else:
        say("Usage: /run-tests [api|ui]")

@app.command("/health-check")
def handle_health_check(ack, say, command):
    ack()
    say("Checking API endpoints...")
    monitor.check_endpoints()
    say("Health check completed")

@app.command("/test-summary")
def handle_test_summary(ack, say, command):
    ack()
    
    api_results = test_runner.run_api_tests()
    ui_results = test_runner.run_ui_tests()
    
    message = f"Test Summary Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    message += f"API Tests: {api_results['passed']}/{api_results['total']} passed\n"
    message += f"UI Tests: {ui_results['passed']}/{ui_results['total']} passed\n"
    
    total_passed = api_results['passed'] + ui_results['passed']
    total_tests = api_results['total'] + ui_results['total']
    
    message += f"Overall: {total_passed}/{total_tests} tests passing"
    
    say(message)

def daily_summary():
    channel = os.environ.get("DAILY_SUMMARY_CHANNEL", "#qa-daily")
    
    api_results = test_runner.run_api_tests()
    ui_results = test_runner.run_ui_tests()
    
    message = f"Daily Test Summary - {datetime.now().strftime('%Y-%m-%d')}\n"
    message += f"API Tests: {api_results['passed']}/{api_results['total']}\n"
    message += f"UI Tests: {ui_results['passed']}/{ui_results['total']}\n"
    
    try:
        client.chat_postMessage(channel=channel, text=message)
    except SlackApiError:
        pass

def scheduled_health_check():
    monitor.check_endpoints()

def run_scheduler():
    schedule.every().day.at("09:00").do(daily_summary)
    schedule.every(15).minutes.do(scheduled_health_check)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_bot():
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

if __name__ == "__main__":
    start_bot()