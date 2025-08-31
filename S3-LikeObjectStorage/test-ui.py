#!/usr/bin/env python3
"""
S3 Storage System - Web UI Testing Script
Automated UI testing using Selenium
"""

import os
import sys
import time
import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuration
UI_URL = os.getenv("UI_URL", "http://localhost:9347")
API_KEY = os.getenv("API_KEY", "")

class UITester:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.test_results = []
        
    def setup_driver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            return True
        except Exception as e:
            print(f"❌ Failed to setup Chrome driver: {e}")
            print("Please install ChromeDriver: https://chromedriver.chromium.org/")
            return False
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅" if passed else "❌"
        print(f"  [{status}] {test_name}")
        if details and not passed:
            print(f"        Details: {details}")
        self.test_results.append((test_name, passed, details))
    
    def test_login_page(self):
        """Test login page functionality"""
        print("\n🔐 Testing Login Page")
        
        try:
            self.driver.get(UI_URL)
            
            # Check if login page loads
            self.wait.until(EC.presence_of_element_located((By.ID, "api_key")))
            self.log_test("Login page loads", True)
            
            # Check page title
            title_correct = "Login" in self.driver.title
            self.log_test("Page title contains 'Login'", title_correct)
            
            # Test empty form submission
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            time.sleep(1)
            
            # Should stay on login page with empty key
            still_on_login = "api_key" in self.driver.current_url or self.driver.find_elements(By.ID, "api_key")
            self.log_test("Empty form submission handled", still_on_login)
            
            # Test with invalid API key
            api_key_input = self.driver.find_element(By.ID, "api_key")
            api_key_input.clear()
            api_key_input.send_keys("invalid_key")
            submit_btn.click()
            time.sleep(2)
            
            # Should show error or stay on login page
            still_on_login = bool(self.driver.find_elements(By.ID, "api_key"))
            self.log_test("Invalid API key rejected", still_on_login)
            
            # Test with valid API key
            if API_KEY:
                api_key_input = self.driver.find_element(By.ID, "api_key")
                api_key_input.clear()
                api_key_input.send_keys(API_KEY)
                submit_btn.click()
                
                # Wait for redirect to dashboard
                try:
                    self.wait.until(lambda driver: "login" not in driver.current_url.lower())
                    self.log_test("Valid API key login successful", True)
                    return True
                except TimeoutException:
                    self.log_test("Valid API key login successful", False, "Timeout waiting for redirect")
                    return False
            else:
                self.log_test("Valid API key login test", False, "No API key provided")
                return False
                
        except Exception as e:
            self.log_test("Login page test", False, str(e))
            return False
    
    def test_dashboard(self):
        """Test dashboard functionality"""
        print("\n📊 Testing Dashboard")
        
        try:
            # Should be on dashboard after login
            dashboard_loaded = "dashboard" in self.driver.current_url.lower() or "Dashboard" in self.driver.page_source
            self.log_test("Dashboard loads after login", dashboard_loaded)
            
            # Check for statistics cards
            stat_cards = self.driver.find_elements(By.CSS_SELECTOR, ".card.bg-primary, .card.bg-success, .card.bg-info")
            self.log_test("Statistics cards present", len(stat_cards) >= 3)
            
            # Check for navigation
            nav_items = self.driver.find_elements(By.CSS_SELECTOR, ".navbar-nav .nav-link")
            self.log_test("Navigation menu present", len(nav_items) >= 2)
            
            # Check for quick actions
            create_bucket_btn = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Create')]")
            self.log_test("Create bucket button present", len(create_bucket_btn) > 0)
            
            return True
            
        except Exception as e:
            self.log_test("Dashboard test", False, str(e))
            return False
    
    def test_bucket_operations(self):
        """Test bucket creation and management"""
        print("\n🪣 Testing Bucket Operations")
        
        test_bucket_name = f"ui-test-{int(time.time())}"
        
        try:
            # Navigate to buckets page
            buckets_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Buckets')]")
            buckets_link.click()
            time.sleep(2)
            
            buckets_page_loaded = "buckets" in self.driver.current_url.lower() or "Buckets" in self.driver.page_source
            self.log_test("Buckets page loads", buckets_page_loaded)
            
            # Click create bucket button
            create_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Create')]"))
            )
            create_btn.click()
            
            # Wait for modal to appear
            modal = self.wait.until(EC.presence_of_element_located((By.ID, "createBucketModal")))
            self.log_test("Create bucket modal opens", modal.is_displayed())
            
            # Fill in bucket name
            bucket_name_input = self.driver.find_element(By.ID, "bucketName")
            bucket_name_input.send_keys(test_bucket_name)
            
            # Click create button in modal
            modal_create_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Create Bucket')]")
            modal_create_btn.click()
            
            # Wait a moment for creation
            time.sleep(3)
            
            # Check if bucket appears in list (refresh page)
            self.driver.refresh()
            time.sleep(2)
            
            bucket_created = test_bucket_name in self.driver.page_source
            self.log_test(f"Bucket '{test_bucket_name}' created successfully", bucket_created)
            
            if bucket_created:
                # Test opening bucket
                try:
                    bucket_link = self.driver.find_element(By.XPATH, f"//a[contains(@href, '{test_bucket_name}')]")
                    bucket_link.click()
                    time.sleep(2)
                    
                    bucket_detail_loaded = test_bucket_name in self.driver.page_source
                    self.log_test("Bucket detail page loads", bucket_detail_loaded)
                    
                    # Test going back to buckets list
                    buckets_breadcrumb = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Buckets')]")
                    buckets_breadcrumb.click()
                    time.sleep(2)
                    
                except Exception as e:
                    self.log_test("Bucket detail page navigation", False, str(e))
            
            return bucket_created
            
        except Exception as e:
            self.log_test("Bucket operations test", False, str(e))
            return False
    
    def test_file_operations(self):
        """Test file upload and download"""
        print("\n📁 Testing File Operations")
        
        test_bucket_name = f"ui-test-{int(time.time())}"
        
        try:
            # First create a bucket for testing
            self.driver.get(f"{UI_URL}/buckets")
            time.sleep(2)
            
            # Create test bucket via UI
            create_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Create')]"))
            )
            create_btn.click()
            
            bucket_name_input = self.wait.until(EC.presence_of_element_located((By.ID, "bucketName")))
            bucket_name_input.send_keys(test_bucket_name)
            
            modal_create_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Create Bucket')]")
            modal_create_btn.click()
            time.sleep(3)
            
            # Navigate to bucket
            self.driver.get(f"{UI_URL}/buckets/{test_bucket_name}")
            time.sleep(2)
            
            bucket_page_loaded = test_bucket_name in self.driver.page_source
            self.log_test("Test bucket created and accessible", bucket_page_loaded)
            
            if bucket_page_loaded:
                # Check for upload button
                upload_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Upload')]")
                self.log_test("Upload button present", len(upload_btns) > 0)
                
                if upload_btns:
                    upload_btns[0].click()
                    time.sleep(1)
                    
                    # Check if upload modal opens
                    upload_modal = self.driver.find_elements(By.ID, "uploadModal")
                    self.log_test("Upload modal opens", len(upload_modal) > 0 and upload_modal[0].is_displayed())
                    
                    # Close modal
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, "#uploadModal .btn-close")
                    close_btn.click()
                    time.sleep(1)
                
                # Check for empty bucket message
                empty_message = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'empty') or contains(text(), 'No objects')]")
                self.log_test("Empty bucket message displayed", len(empty_message) > 0)
            
            return True
            
        except Exception as e:
            self.log_test("File operations test", False, str(e))
            return False
    
    def test_navigation_and_ui_elements(self):
        """Test general UI navigation and elements"""
        print("\n🧭 Testing Navigation and UI Elements")
        
        try:
            # Test navigation menu
            nav_links = self.driver.find_elements(By.CSS_SELECTOR, ".navbar-nav .nav-link")
            self.log_test("Navigation menu has links", len(nav_links) >= 2)
            
            # Test account dropdown
            account_dropdown = self.driver.find_elements(By.CSS_SELECTOR, ".navbar-nav .dropdown-toggle")
            self.log_test("Account dropdown present", len(account_dropdown) > 0)
            
            if account_dropdown:
                account_dropdown[0].click()
                time.sleep(1)
                
                logout_link = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Logout')]")
                self.log_test("Logout link in dropdown", len(logout_link) > 0)
                
                # Click somewhere else to close dropdown
                self.driver.find_element(By.TAG_NAME, "body").click()
            
            # Test responsive design elements
            self.driver.set_window_size(768, 1024)  # Mobile size
            time.sleep(1)
            
            # Check if navbar collapses
            navbar_toggler = self.driver.find_elements(By.CSS_SELECTOR, ".navbar-toggler")
            self.log_test("Navbar responsive (mobile view)", len(navbar_toggler) > 0)
            
            # Reset to desktop size
            self.driver.set_window_size(1920, 1080)
            time.sleep(1)
            
            return True
            
        except Exception as e:
            self.log_test("Navigation and UI test", False, str(e))
            return False
    
    def test_error_handling(self):
        """Test error handling and edge cases"""
        print("\n⚠️ Testing Error Handling")
        
        try:
            # Test accessing non-existent bucket
            self.driver.get(f"{UI_URL}/buckets/non-existent-bucket-12345")
            time.sleep(2)
            
            # Should show error or redirect
            error_handled = ("error" in self.driver.page_source.lower() or 
                           "not found" in self.driver.page_source.lower() or
                           "buckets" in self.driver.current_url)
            self.log_test("Non-existent bucket handled gracefully", error_handled)
            
            # Test invalid bucket name creation
            self.driver.get(f"{UI_URL}/buckets")
            time.sleep(2)
            
            create_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Create')]")
            create_btn.click()
            
            bucket_name_input = self.wait.until(EC.presence_of_element_located((By.ID, "bucketName")))
            bucket_name_input.send_keys("INVALID-BUCKET-NAME")  # Uppercase not allowed
            
            modal_create_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Create Bucket')]")
            modal_create_btn.click()
            time.sleep(2)
            
            # Should show error (modal might stay open or show alert)
            modal_still_open = self.driver.find_elements(By.ID, "createBucketModal")
            error_alert = self.driver.find_elements(By.CSS_SELECTOR, ".alert-danger")
            
            error_handled = (len(modal_still_open) > 0 or len(error_alert) > 0)
            self.log_test("Invalid bucket name handled", error_handled)
            
            return True
            
        except Exception as e:
            self.log_test("Error handling test", False, str(e))
            return False
    
    def test_logout(self):
        """Test logout functionality"""
        print("\n🚪 Testing Logout")
        
        try:
            # Click account dropdown
            account_dropdown = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".navbar-nav .dropdown-toggle"))
            )
            account_dropdown.click()
            time.sleep(1)
            
            # Click logout
            logout_link = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Logout')]"))
            )
            logout_link.click()
            
            # Should redirect to login page
            self.wait.until(EC.presence_of_element_located((By.ID, "api_key")))
            
            back_to_login = "login" in self.driver.current_url.lower() or bool(self.driver.find_elements(By.ID, "api_key"))
            self.log_test("Logout redirects to login page", back_to_login)
            
            return back_to_login
            
        except Exception as e:
            self.log_test("Logout test", False, str(e))
            return False
    
    def run_all_tests(self):
        """Run all UI tests"""
        print("🌐 S3 Storage System - Web UI Testing")
        print("=" * 50)
        print(f"UI URL: {UI_URL}")
        print(f"API Key: {'Set' if API_KEY else 'Not set'}")
        
        if not API_KEY:
            print("❌ ERROR: API_KEY environment variable not set")
            print("Usage: API_KEY=your_api_key python test-ui.py")
            return False
        
        if not self.setup_driver():
            return False
        
        try:
            start_time = time.time()
            
            # Run test sequence
            login_success = self.test_login_page()
            if login_success:
                self.test_dashboard()
                self.test_bucket_operations()
                self.test_file_operations()
                self.test_navigation_and_ui_elements()
                self.test_error_handling()
                self.test_logout()
            else:
                print("⚠️ Skipping remaining tests due to login failure")
            
            # Summary
            duration = time.time() - start_time
            total_tests = len(self.test_results)
            passed_tests = sum(1 for _, passed, _ in self.test_results if passed)
            failed_tests = total_tests - passed_tests
            
            print(f"\n{'='*50}")
            print(f"UI Test Summary")
            print(f"{'='*50}")
            print(f"Total Tests: {total_tests}")
            print(f"Passed: {passed_tests}")
            print(f"Failed: {failed_tests}")
            print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
            print(f"Duration: {duration:.2f} seconds")
            
            if failed_tests > 0:
                print(f"\n❌ Failed Tests:")
                for test_name, passed, details in self.test_results:
                    if not passed:
                        print(f"  - {test_name}")
                        if details:
                            print(f"    {details}")
            
            return passed_tests == total_tests
            
        finally:
            if self.driver:
                self.driver.quit()

def main():
    """Main test runner"""
    tester = UITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()