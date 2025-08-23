import pytest
import requests
import json
import allure
from datetime import datetime

BASE_URL = "https://api.example.com"

class TestAuthAPI:
    
    @allure.feature("Authentication")
    @allure.story("User Login")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_valid_credentials(self):
        payload = {
            "username": "testuser",
            "password": "testpass123"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=payload)
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
    
    @allure.feature("Authentication")
    @allure.story("User Login")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_invalid_credentials(self):
        payload = {
            "username": "invalid",
            "password": "wrong"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=payload)
        
        assert response.status_code == 401
        assert "error" in response.json()
    
    @allure.feature("Authentication")
    @allure.story("Token Validation")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_token_validation(self):
        login_payload = {
            "username": "testuser",
            "password": "testpass123"
        }
        
        login_response = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/auth/validate", headers=headers)
        
        assert response.status_code == 200
        assert response.json()["valid"] is True

class TestUsersAPI:
    
    @allure.feature("User Management")
    @allure.story("Get Users")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_users_list(self):
        response = requests.get(f"{BASE_URL}/users")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @allure.feature("User Management")
    @allure.story("Create User")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_user(self):
        payload = {
            "username": f"testuser_{datetime.now().timestamp()}",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = requests.post(f"{BASE_URL}/users", json=payload)
        
        assert response.status_code == 201
        assert response.json()["username"] == payload["username"]
    
    @allure.feature("User Management")
    @allure.story("Update User")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_user(self):
        user_id = 1
        payload = {
            "first_name": "Updated",
            "last_name": "Name"
        }
        
        response = requests.put(f"{BASE_URL}/users/{user_id}", json=payload)
        
        assert response.status_code == 200
        assert response.json()["first_name"] == "Updated"
    
    @allure.feature("User Management")
    @allure.story("Delete User")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_user(self):
        user_id = 999
        
        response = requests.delete(f"{BASE_URL}/users/{user_id}")
        
        assert response.status_code in [200, 204, 404]

class TestAPIPerformance:
    
    @allure.feature("Performance")
    @allure.story("Response Time")
    @allure.severity(allure.severity_level.NORMAL)
    def test_api_response_time(self):
        import time
        
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/health")
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        
        assert response.status_code == 200
        assert response_time < 1000
    
    @allure.feature("Performance")
    @allure.story("Concurrent Requests")
    @allure.severity(allure.severity_level.NORMAL)
    def test_concurrent_requests(self):
        import concurrent.futures
        
        def make_request():
            return requests.get(f"{BASE_URL}/health")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        for response in responses:
            assert response.status_code == 200

class TestAPISecurity:
    
    @allure.feature("Security")
    @allure.story("SQL Injection")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_sql_injection_protection(self):
        malicious_payload = {
            "username": "admin'; DROP TABLE users; --",
            "password": "password"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=malicious_payload)
        
        assert response.status_code in [400, 401, 422]
    
    @allure.feature("Security")
    @allure.story("XSS Protection")
    @allure.severity(allure.severity_level.NORMAL)
    def test_xss_protection(self):
        malicious_payload = {
            "username": "<script>alert('xss')</script>",
            "email": "test@example.com"
        }
        
        response = requests.post(f"{BASE_URL}/users", json=malicious_payload)
        
        if response.status_code == 201:
            user_data = response.json()
            assert "<script>" not in user_data["username"]
    
    @allure.feature("Security")
    @allure.story("Rate Limiting")
    @allure.severity(allure.severity_level.NORMAL)
    def test_rate_limiting(self):
        for _ in range(100):
            response = requests.get(f"{BASE_URL}/health")
        
        assert response.status_code in [200, 429]

class TestDataValidation:
    
    @allure.feature("Data Validation")
    @allure.story("Required Fields")
    @allure.severity(allure.severity_level.NORMAL)
    def test_missing_required_fields(self):
        payload = {
            "email": "test@example.com"
        }
        
        response = requests.post(f"{BASE_URL}/users", json=payload)
        
        assert response.status_code in [400, 422]
    
    @allure.feature("Data Validation")
    @allure.story("Field Format Validation")
    @allure.severity(allure.severity_level.NORMAL)
    def test_invalid_email_format(self):
        payload = {
            "username": "testuser",
            "email": "invalid-email",
            "first_name": "Test"
        }
        
        response = requests.post(f"{BASE_URL}/users", json=payload)
        
        assert response.status_code in [400, 422]