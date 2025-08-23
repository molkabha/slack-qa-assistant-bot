from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess
import os
from pathlib import Path
import json
from datetime import datetime
import uvicorn

app = FastAPI(title="QA Assistant API", version="1.0.0")

if Path("reports/allure-report").exists():
    app.mount("/allure-report", StaticFiles(directory="reports/allure-report"), name="allure-report")

if Path("reports/allure-report-ui").exists():
    app.mount("/allure-report-ui", StaticFiles(directory="reports/allure-report-ui"), name="allure-report-ui")

class TestRequest(BaseModel):
    test_type: str
    suite: str = None

class TestResult(BaseModel):
    total: int
    passed: int
    failed: int
    skipped: int
    duration: float
    report_url: str = None

class HealthCheck(BaseModel):
    endpoint: str
    status: str
    response_time: float
    timestamp: datetime

def run_tests_background(test_type: str, suite: str = None):
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    if test_type == "api":
        if suite:
            test_path = f"tests/test_{suite}.py"
        else:
            test_path = "tests/test_api.py"
        
        allure_dir = "reports/allure-results"
        results_file = "reports/api_results.json"
        report_dir = "reports/allure-report"
        
    elif test_type == "ui":
        if suite:
            test_path = f"tests/ui/test_{suite}.py"
        else:
            test_path = "tests/test_ui.py"
        
        allure_dir = "reports/allure-results-ui"
        results_file = "reports/ui_results.json"
        report_dir = "reports/allure-report-ui"
    
    else:
        raise ValueError("Invalid test type")
    
    cmd = [
        "pytest", test_path,
        f"--alluredir={allure_dir}",
        "--json-report",
        f"--json-report-file={results_file}",
        "-v"
    ]
    
    subprocess.run(cmd, capture_output=True, text=True)
    
    subprocess.run([
        "allure", "generate",
        allure_dir,
        "-o", report_dir,
        "--clean"
    ])

def parse_test_results(results_file: str) -> dict:
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
        return {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration": 0}

@app.get("/")
async def root():
    return {"message": "QA Assistant API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/run-tests", response_model=TestResult)
async def run_tests(request: TestRequest, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(run_tests_background, request.test_type, request.suite)
        
        if request.test_type == "api":
            results_file = "reports/api_results.json"
            report_url = "/allure-report"
        elif request.test_type == "ui":
            results_file = "reports/ui_results.json"
            report_url = "/allure-report-ui"
        else:
            raise HTTPException(status_code=400, detail="Invalid test type")
        
        results = parse_test_results(results_file)
        results["report_url"] = report_url
        
        return TestResult(**results)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-results/{test_type}")
async def get_test_results(test_type: str):
    if test_type not in ["api", "ui"]:
        raise HTTPException(status_code=400, detail="Invalid test type")
    
    results_file = f"reports/{test_type}_results.json"
    
    if not Path(results_file).exists():
        raise HTTPException(status_code=404, detail="Test results not found")
    
    results = parse_test_results(results_file)
    return results

@app.get("/reports/{test_type}")
async def get_report(test_type: str):
    if test_type not in ["api", "ui"]:
        raise HTTPException(status_code=400, detail="Invalid test type")
    
    if test_type == "api":
        report_path = "reports/allure-report/index.html"
    else:
        report_path = "reports/allure-report-ui/index.html"
    
    if not Path(report_path).exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(report_path)

@app.get("/summary")
async def get_test_summary():
    api_results = parse_test_results("reports/api_results.json")
    ui_results = parse_test_results("reports/ui_results.json")
    
    return {
        "timestamp": datetime.now(),
        "api_tests": api_results,
        "ui_tests": ui_results,
        "total_passed": api_results["passed"] + ui_results["passed"],
        "total_failed": api_results["failed"] + ui_results["failed"],
        "total_tests": api_results["total"] + ui_results["total"]
    }

@app.post("/health-check")
async def perform_health_check():
    endpoints = [
        {"name": "Auth API", "url": "https://api.example.com/auth"},
        {"name": "Users API", "url": "https://api.example.com/users"},
        {"name": "Health Check", "url": "https://api.example.com/health"}
    ]
    
    results = []
    
    for endpoint in endpoints:
        try:
            import requests
            import time
            
            start_time = time.time()
            response = requests.get(endpoint["url"], timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            status = "healthy" if response.status_code == 200 else "unhealthy"
            
            results.append(HealthCheck(
                endpoint=endpoint["name"],
                status=status,
                response_time=response_time,
                timestamp=datetime.now()
            ))
        
        except Exception:
            results.append(HealthCheck(
                endpoint=endpoint["name"],
                status="error",
                response_time=0,
                timestamp=datetime.now()
            ))
    
    return {"endpoints": results}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)