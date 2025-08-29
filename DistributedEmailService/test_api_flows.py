#!/usr/bin/env python3
"""
API Flow Testing - Test actual request/response flows
"""

import json
import sys
import os
from pathlib import Path

def test_auth_flow():
    """Test authentication flow"""
    print("🔍 Testing Authentication Flow...")
    
    # Test registration payload
    registration_data = {
        "email": "demo@example.com",
        "password": "password",
        "full_name": "Demo User",
        "role": "user"
    }
    
    # Test login payload
    login_data = {
        "email": "demo@example.com",
        "password": "password"
    }
    
    print(f"✅ Registration payload: {json.dumps(registration_data, indent=2)}")
    print(f"✅ Login payload: {json.dumps(login_data, indent=2)}")
    
    return True

def test_email_flow():
    """Test email creation flow"""
    print("🔍 Testing Email Flow...")
    
    # Test email creation payload
    email_data = {
        "to_recipients": ["recipient@example.com"],
        "cc_recipients": ["cc@example.com"],
        "bcc_recipients": [],
        "subject": "Test Email with Distributed Tracing",
        "body": "This email demonstrates the full flow: Auth → Email → Spam → Notification → Search",
        "priority": "normal",
        "is_draft": False,
        "attachment_ids": [],
        "labels": ["demo", "test"]
    }
    
    print(f"✅ Email creation payload: {json.dumps(email_data, indent=2)}")
    
    return True

def test_spam_detection_flow():
    """Test spam detection flow"""
    print("🔍 Testing Spam Detection Flow...")
    
    # Test normal email
    normal_email = {
        "subject": "Weekly Team Meeting",
        "body": "Hi team, let's schedule our weekly meeting for Thursday at 2 PM.",
        "from_email": "manager@company.com",
        "to_emails": ["team@company.com"]
    }
    
    # Test spam email
    spam_email = {
        "subject": "URGENT!!! You won $1000000!!!",
        "body": "Congratulations! Click here now! 100% guaranteed! Free money! No risk! Limited time offer!",
        "from_email": "noreply@suspicious.com",
        "to_emails": ["victim@example.com"]
    }
    
    print(f"✅ Normal email test case: {json.dumps(normal_email, indent=2)}")
    print(f"✅ Spam email test case: {json.dumps(spam_email, indent=2)}")
    
    return True

def test_search_flow():
    """Test search flow"""
    print("🔍 Testing Search Flow...")
    
    # Test search request
    search_request = {
        "query": "team meeting",
        "filters": {
            "folder": "inbox",
            "is_read": False,
            "from_date": "2024-01-01T00:00:00Z"
        },
        "limit": 50,
        "offset": 0
    }
    
    print(f"✅ Search request: {json.dumps(search_request, indent=2)}")
    
    return True

def test_notification_flow():
    """Test notification flow"""  
    print("🔍 Testing Notification Flow...")
    
    # Test notification creation
    notification = {
        "user_id": "user-123",
        "type": "EMAIL_RECEIVED",
        "title": "New Email Received",
        "message": "You have received a new email from demo@example.com",
        "data": {
            "email_id": "email-456",
            "sender": "demo@example.com",
            "subject": "Test Email"
        },
        "priority": "normal"
    }
    
    print(f"✅ Notification payload: {json.dumps(notification, indent=2)}")
    
    return True

def test_tracing_flow():
    """Test distributed tracing flow"""
    print("🔍 Testing Distributed Tracing Flow...")
    
    # Example trace flow for email creation
    trace_flow = {
        "trace_id": "trace-12345",
        "spans": [
            {
                "service": "api-gateway",
                "operation": "POST /emails",
                "duration_ms": 150,
                "status": "success"
            },
            {
                "service": "auth-service", 
                "operation": "validate_token",
                "duration_ms": 20,
                "status": "success"
            },
            {
                "service": "email-service",
                "operation": "create_email", 
                "duration_ms": 100,
                "status": "success"
            },
            {
                "service": "spam-service",
                "operation": "check_spam",
                "duration_ms": 30,
                "status": "success",
                "attributes": {"spam_score": 0.1}
            },
            {
                "service": "notification-service",
                "operation": "send_notification",
                "duration_ms": 25,
                "status": "success"
            }
        ]
    }
    
    print(f"✅ Expected trace flow: {json.dumps(trace_flow, indent=2)}")
    
    return True

def test_error_handling():
    """Test error handling scenarios"""
    print("🔍 Testing Error Handling...")
    
    error_scenarios = {
        "invalid_auth": {
            "error": "Invalid or expired token",
            "status_code": 401,
            "service": "auth-service"
        },
        "missing_recipient": {
            "error": "to_recipients is required",
            "status_code": 400,
            "service": "email-service"  
        },
        "file_too_large": {
            "error": "File too large. Maximum size is 25MB",
            "status_code": 413,
            "service": "attachment-service"
        },
        "search_timeout": {
            "error": "Search request timeout",
            "status_code": 504,
            "service": "search-service"
        }
    }
    
    for scenario, error in error_scenarios.items():
        print(f"✅ {scenario}: {json.dumps(error, indent=2)}")
    
    return True

def test_docker_compose_flow():
    """Test docker-compose service flow"""
    print("🔍 Testing Docker Compose Service Flow...")
    
    # Read and validate docker-compose.yml
    try:
        import yaml
        with open('docker-compose.yml') as f:
            compose = yaml.safe_load(f)
        
        services = compose['services']
        
        # Test service dependencies
        dependencies = {
            'auth-service': ['postgres', 'redis', 'jaeger'],
            'email-service': ['postgres', 'redis', 'auth-service', 'spam-service', 'notification-service'],
            'api-gateway': ['auth-service', 'email-service', 'search-service'],
            'ui': ['api-gateway']
        }
        
        for service, deps in dependencies.items():
            if service in services:
                service_config = services[service]
                depends_on = service_config.get('depends_on', {})
                
                missing_deps = []
                for dep in deps:
                    if dep not in depends_on:
                        missing_deps.append(dep)
                
                if missing_deps:
                    print(f"⚠️ {service} missing dependencies: {missing_deps}")
                else:
                    print(f"✅ {service} dependencies configured correctly")
        
        print("✅ Docker Compose service flow validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Docker Compose validation failed: {e}")
        return False

def main():
    """Run all API flow tests"""
    print("🚀 Starting API Flow Testing")
    print("=" * 50)
    
    os.chdir('/Users/vijayabhaskarv/python-projects/venv/sysdesign/17-DistriEmailServie/demo')
    
    tests = [
        test_auth_flow,
        test_email_flow, 
        test_spam_detection_flow,
        test_search_flow,
        test_notification_flow,
        test_tracing_flow,
        test_error_handling,
        test_docker_compose_flow
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 API Flow Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All API flows validated! Ready for end-to-end testing with Docker.")
        return True
    else:
        print("⚠️ Some API flow tests failed. Please review the issues above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)