import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import allure
import time

BASE_URL = "https://example.com"

@pytest.fixture(scope="session")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()

class TestLoginPage:
    
    @allure.feature("Authentication")
    @allure.story("Login Form")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_successful_login(self, driver):
        driver.get(f"{BASE_URL}/login")
        
        username_field = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")
        login_button = driver.find_element(By.ID, "login-btn")
        
        username_field.send_keys("testuser")
        password_field.send_keys("testpass123")
        login_button.click()
        
        WebDriverWait(driver, 10).until(
            EC.url_contains("/dashboard")
        )
        
        assert "/dashboard" in driver.current_url
    
    @allure.feature("Authentication")
    @allure.story("Login Form")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_with_invalid_credentials(self, driver):
        driver.get(f"{BASE_URL}/login")
        
        username_field = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")
        login_button = driver.find_element(By.ID, "login-btn")
        
        username_field.clear()
        password_field.clear()
        
        username_field.send_keys("invalid")
        password_field.send_keys("wrong")
        login_button.click()
        
        error_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
        )
        
        assert error_message.is_displayed()
        assert "Invalid credentials" in error_message.text.lower()
    
    @allure.feature("Authentication")
    @allure.story("Form Validation")
    @allure.severity(allure.severity_level.NORMAL)
    def test_empty_login_fields(self, driver):
        driver.get(f"{BASE_URL}/login")
        
        login_button = driver.find_element(By.ID, "login-btn")
        login_button.click()
        
        username_error = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "username-error"))
        )
        
        assert username_error.is_displayed()

class TestDashboardPage:
    
    @allure.feature("Dashboard")
    @allure.story("Page Load")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_dashboard_loads_after_login(self, driver):
        self._login(driver)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
        )
        
        dashboard = driver.find_element(By.CLASS_NAME, "dashboard")
        assert dashboard.is_displayed()
    
    @allure.feature("Dashboard")
    @allure.story("Navigation")
    @allure.severity(allure.severity_level.NORMAL)
    def test_navigation_menu(self, driver):
        self._login(driver)
        
        nav_menu = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "nav-menu"))
        )
        
        menu_items = nav_menu.find_elements(By.TAG_NAME, "a")
        assert len(menu_items) > 0
        
        for item in menu_items:
            assert item.is_displayed()
    
    @allure.feature("Dashboard")
    @allure.story("User Profile")
    @allure.severity(allure.severity_level.NORMAL)
    def test_user_profile_access(self, driver):
        self._login(driver)
        
        profile_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "profile-btn"))
        )
        profile_button.click()
        
        profile_menu = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "profile-menu"))
        )
        
        assert profile_menu.is_displayed()
    
    def _login(self, driver):
        driver.get(f"{BASE_URL}/login")
        
        username_field = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")
        login_button = driver.find_element(By.ID, "login-btn")
        
        username_field.send_keys("testuser")
        password_field.send_keys("testpass123")
        login_button.click()
        
        WebDriverWait(driver, 10).until(
            EC.url_contains("/dashboard")
        )

class TestUserManagement:
    
    @allure.feature("User Management")
    @allure.story("Create User")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_new_user(self, driver):
        self._login_as_admin(driver)
        
        driver.get(f"{BASE_URL}/users/new")
        
        first_name = driver.find_element(By.ID, "first_name")
        last_name = driver.find_element(By.ID, "last_name")
        email = driver.find_element(By.ID, "email")
        username = driver.find_element(By.ID, "username")
        submit_btn = driver.find_element(By.ID, "submit-btn")
        
        timestamp = str(int(time.time()))
        
        first_name.send_keys("Test")
        last_name.send_keys("User")
        email.send_keys(f"testuser{timestamp}@example.com")
        username.send_keys(f"testuser{timestamp}")
        submit_btn.click()
        
        success_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
        )
        
        assert success_message.is_displayed()
    
    @allure.feature("User Management")
    @allure.story("Edit User")
    @allure.severity(allure.severity_level.NORMAL)
    def test_edit_user(self, driver):
        self._login_as_admin(driver)
        
        driver.get(f"{BASE_URL}/users")
        
        first_user_edit = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "edit-user-btn"))
        )
        first_user_edit.click()
        
        first_name = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "first_name"))
        )
        
        first_name.clear()
        first_name.send_keys("Updated Name")
        
        save_btn = driver.find_element(By.ID, "save-btn")
        save_btn.click()
        
        success_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
        )
        
        assert success_message.is_displayed()
    
    def _login_as_admin(self, driver):
        driver.get(f"{BASE_URL}/login")
        
        username_field = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")
        login_button = driver.find_element(By.ID, "login-btn")
        
        username_field.send_keys("admin")
        password_field.send_keys("adminpass123")
        login_button.click()
        
        WebDriverWait(driver, 10).until(
            EC.url_contains("/dashboard")
        )

class TestResponsiveDesign:
    
    @allure.feature("Responsive Design")
    @allure.story("Mobile View")
    @allure.severity(allure.severity_level.NORMAL)
    def test_mobile_responsive(self, driver):
        driver.set_window_size(375, 667)
        driver.get(f"{BASE_URL}")
        
        mobile_menu = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "mobile-menu-btn"))
        )
        
        assert mobile_menu.is_displayed()
        
        driver.set_window_size(1920, 1080)
    
    @allure.feature("Responsive Design")
    @allure.story("Tablet View")
    @allure.severity(allure.severity_level.NORMAL)
    def test_tablet_responsive(self, driver):
        driver.set_window_size(768, 1024)
        driver.get(f"{BASE_URL}")
        
        navigation = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "navigation"))
        )
        
        assert navigation.is_displayed()
        
        driver.set_window_size(1920, 1080)

class TestFormValidation:
    
    @allure.feature("Form Validation")
    @allure.story("Contact Form")
    @allure.severity(allure.severity_level.NORMAL)
    def test_contact_form_validation(self, driver):
        driver.get(f"{BASE_URL}/contact")
        
        submit_btn = driver.find_element(By.ID, "submit-btn")
        submit_btn.click()
        
        name_error = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "name-error"))
        )
        email_error = driver.find_element(By.ID, "email-error")
        message_error = driver.find_element(By.ID, "message-error")
        
        assert name_error.is_displayed()
        assert email_error.is_displayed()
        assert message_error.is_displayed()
    
    @allure.feature("Form Validation")
    @allure.story("Email Format")
    @allure.severity(allure.severity_level.NORMAL)
    def test_invalid_email_format(self, driver):
        driver.get(f"{BASE_URL}/contact")
        
        email_field = driver.find_element(By.ID, "email")
        email_field.send_keys("invalid-email")
        
        submit_btn = driver.find_element(By.ID, "submit-btn")
        submit_btn.click()
        
        email_error = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "email-error"))
        )
        
        assert email_error.is_displayed()
        assert "valid email" in email_error.text.lower()