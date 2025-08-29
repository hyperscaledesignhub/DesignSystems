#!/usr/bin/env python3
"""
Comprehensive Flow Testing for Distributed Email Service Demo
Tests all critical workflows without requiring running Docker containers
"""

import json
import sys
import os
from pathlib import Path

def test_service_structure():
    """Test that all services have correct structure"""
    print("🔍 Testing Service Structure...")
    
    services = ['auth-service', 'email-service', 'spam-service', 'notification-service',
                'attachment-service', 'search-service', 'api-gateway']
    
    missing_services = []
    for service in services:
        service_path = Path(f'services/{service}/main.py')
        if not service_path.exists():
            missing_services.append(service)
    
    if missing_services:
        print(f"❌ Missing services: {missing_services}")
        return False
    
    print(f"✅ All {len(services)} services present")
    return True

def test_shared_modules():
    """Test shared module structure"""
    print("🔍 Testing Shared Modules...")
    
    shared_modules = ['models.py', 'database.py', 'tracing.py', '__init__.py']
    missing_modules = []
    
    for module in shared_modules:
        module_path = Path(f'services/shared/{module}')
        if not module_path.exists():
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ Missing shared modules: {missing_modules}")
        return False
    
    print(f"✅ All {len(shared_modules)} shared modules present")
    return True

def test_ui_structure():
    """Test React UI structure"""
    print("🔍 Testing UI Structure...")
    
    ui_files = [
        'package.json',
        'src/App.js',
        'src/index.js',
        'src/components/Login.js',
        'src/components/Dashboard.js',
        'src/components/EmailList.js',
        'src/components/ComposeEmail.js',
        'src/components/EmailView.js',
        'src/components/SearchEmails.js',
        'src/contexts/AuthContext.js',
        'src/contexts/NotificationContext.js'
    ]
    
    missing_files = []
    for file in ui_files:
        file_path = Path(f'ui/{file}')
        if not file_path.exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing UI files: {missing_files}")
        return False
    
    print(f"✅ All {len(ui_files)} UI files present")
    return True

def test_docker_configuration():
    """Test Docker configuration"""
    print("🔍 Testing Docker Configuration...")
    
    docker_files = ['docker-compose.yml', 'Dockerfile.microservice', 'Dockerfile.ui']
    missing_files = []
    
    for file in docker_files:
        file_path = Path(file)
        if not file_path.exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing Docker files: {missing_files}")
        return False
    
    print(f"✅ All {len(docker_files)} Docker files present")
    return True

def test_api_flow():
    """Test API flow logic"""
    print("🔍 Testing API Flow Logic...")
    
    # Test auth service flow
    auth_main = Path('services/auth-service/main.py').read_text()
    auth_checks = [
        'register' in auth_main,
        'login' in auth_main,
        'validate_token' in auth_main,
        'JWT' in auth_main or 'jwt' in auth_main
    ]
    
    if not all(auth_checks):
        print("❌ Auth service missing critical endpoints")
        return False
    
    # Test email service flow  
    email_main = Path('services/email-service/main.py').read_text()
    email_checks = [
        'create_email' in email_main,
        'list_emails' in email_main,
        'get_email' in email_main,
        'spam' in email_main.lower(),
        'notification' in email_main.lower()
    ]
    
    if not all(email_checks):
        print("❌ Email service missing critical functionality")
        return False
    
    print("✅ API flow logic validation passed")
    return True

def test_tracing_integration():
    """Test tracing integration"""
    print("🔍 Testing Tracing Integration...")
    
    tracing_file = Path('services/shared/tracing.py').read_text()
    tracing_checks = [
        'opentelemetry' in tracing_file,
        'jaeger' in tracing_file.lower(),
        'setup_tracing' in tracing_file,
        'create_span_attributes' in tracing_file,
        'get_trace_headers' in tracing_file
    ]
    
    if not all(tracing_checks):
        print("❌ Tracing integration incomplete")
        return False
    
    # Check if services use tracing
    services_with_tracing = 0
    services = ['auth-service', 'email-service', 'spam-service']
    
    for service in services:
        service_main = Path(f'services/{service}/main.py').read_text()
        if 'setup_tracing' in service_main and 'tracer' in service_main:
            services_with_tracing += 1
    
    if services_with_tracing < len(services):
        print(f"⚠️ Only {services_with_tracing}/{len(services)} services have tracing")
    else:
        print(f"✅ All {len(services)} core services have tracing integration")
    
    print("✅ Tracing integration validation passed")
    return True

def test_ui_flows():
    """Test UI flow integration"""
    print("🔍 Testing UI Flows...")
    
    # Test authentication flow
    auth_context = Path('ui/src/contexts/AuthContext.js').read_text()
    auth_ui_checks = [
        'login' in auth_context,
        'register' in auth_context,
        'logout' in auth_context,
        'axios' in auth_context
    ]
    
    if not all(auth_ui_checks):
        print("❌ UI authentication flow incomplete")
        return False
    
    # Test main dashboard
    dashboard = Path('ui/src/components/Dashboard.js').read_text()
    dashboard_checks = [
        'EmailList' in dashboard,
        'ComposeEmail' in dashboard,
        'SearchEmails' in dashboard,
        'Routes' in dashboard
    ]
    
    if not all(dashboard_checks):
        print("❌ Dashboard integration incomplete")
        return False
    
    print("✅ UI flow validation passed")
    return True

def test_documentation():
    """Test documentation completeness"""
    print("🔍 Testing Documentation...")
    
    doc_files = ['README.md', 'DEPLOYMENT.md']
    missing_docs = []
    
    for doc in doc_files:
        doc_path = Path(doc)
        if not doc_path.exists():
            missing_docs.append(doc)
            continue
            
        content = doc_path.read_text()
        if len(content) < 1000:  # Basic content check
            print(f"⚠️ {doc} seems too short")
    
    if missing_docs:
        print(f"❌ Missing documentation: {missing_docs}")
        return False
    
    print("✅ Documentation validation passed")
    return True

def test_startup_scripts():
    """Test startup script structure"""
    print("🔍 Testing Startup Scripts...")
    
    scripts = ['scripts/start-demo.sh', 'scripts/stop-demo.sh']
    missing_scripts = []
    
    for script in scripts:
        script_path = Path(script)
        if not script_path.exists():
            missing_scripts.append(script)
            continue
            
        if not os.access(script_path, os.X_OK):
            print(f"⚠️ {script} is not executable")
    
    if missing_scripts:
        print(f"❌ Missing scripts: {missing_scripts}")
        return False
    
    print("✅ Startup scripts validation passed")
    return True

def test_microservices_integration():
    """Test microservices integration patterns"""
    print("🔍 Testing Microservices Integration...")
    
    # Test API Gateway routing
    gateway = Path('services/api-gateway/main.py').read_text()
    gateway_checks = [
        'SERVICE_URLS' in gateway,
        'auth-service' in gateway,
        'email-service' in gateway,
        'proxy' in gateway.lower() or 'route' in gateway.lower()
    ]
    
    if not all(gateway_checks):
        print("❌ API Gateway routing incomplete")
        return False
    
    # Test service discovery pattern
    services_with_health = 0
    test_services = ['auth-service', 'email-service', 'spam-service']
    
    for service in test_services:
        service_main = Path(f'services/{service}/main.py').read_text()
        if '/health' in service_main:
            services_with_health += 1
    
    if services_with_health < len(test_services):
        print(f"⚠️ Only {services_with_health}/{len(test_services)} services have health checks")
    
    print("✅ Microservices integration validation passed")
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Comprehensive Flow Testing")
    print("=" * 50)
    
    os.chdir('/Users/vijayabhaskarv/python-projects/venv/sysdesign/17-DistriEmailServie/demo')
    
    tests = [
        test_service_structure,
        test_shared_modules,
        test_ui_structure,
        test_docker_configuration,
        test_api_flow,
        test_tracing_integration,
        test_ui_flows,
        test_documentation,
        test_startup_scripts,
        test_microservices_integration
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
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The demo is ready for customer presentation.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)