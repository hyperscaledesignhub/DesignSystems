#!/usr/bin/env python3
"""
Professional Test Runner for Distributed Database Demos

This module provides a professional way to run all demos with:
- Temporary directory management
- Proper cleanup after each test
- Test isolation
- Professional logging
- Error handling and reporting
"""

import os
import sys
import time
import importlib.util
from typing import List, Dict, Optional
from test_utils import TestEnvironment, global_test_cleanup

class ProfessionalTestRunner:
    """Professional test runner for distributed database demos"""
    
    def __init__(self):
        self.test_results = {}
        self.demos = {
            'vector_clock_db': {
                'file': 'vector_clock_db_demo.py',
                'description': 'Vector clock functionality with causal consistency',
                'timeout': 120
            },
            'convergence': {
                'file': 'convergence_test.py',
                'description': 'Multi-node convergence and conflict resolution',
                'timeout': 90
            },
            'anti_entropy': {
                'file': 'working_anti_entropy_demo.py',
                'description': 'Anti-entropy synchronization between nodes',
                'timeout': 120
            },
            'automated_anti_entropy': {
                'file': 'automated_anti_entropy_demo.py',
                'description': 'Automated anti-entropy with data verification',
                'timeout': 180
            },
            'consistent_hashing': {
                'file': 'consistent_hashing_demo.py',
                'description': 'Consistent hashing and data distribution',
                'timeout': 90
            },
            'replication': {
                'file': 'replication_demo.py',
                'description': 'Data replication and consistency',
                'timeout': 120
            },
            'persistence_anti_entropy': {
                'file': 'demo_persistence_anti_entropy.py',
                'description': 'Persistence with anti-entropy',
                'timeout': 150
            }
        }
    
    def run_demo(self, demo_name: str, config_file: str = "yaml/config-local.yaml", use_existing: bool = True) -> bool:
        """Run a single demo with professional testing practices"""
        if demo_name not in self.demos:
            print(f"❌ Unknown demo: {demo_name}")
            return False
        
        demo_info = self.demos[demo_name]
        demo_file = demo_info['file']
        
        print(f"\n🎬 Running Demo: {demo_name}")
        print(f"📝 Description: {demo_info['description']}")
        print(f"⏱️ Timeout: {demo_info['timeout']}s")
        print(f"📁 Config: {config_file}")
        print(f"🔧 Mode: {'Existing cluster' if use_existing else 'New cluster'}")
        print("=" * 80)
        
        # Use test environment for proper cleanup
        with TestEnvironment(f"demo_{demo_name}") as test_env:
            try:
                # Set environment variables for the demo
                os.environ['CONFIG_FILE'] = config_file
                os.environ['USE_EXISTING_CLUSTER'] = str(use_existing)
                os.environ['TEST_DATA_DIR'] = test_env.test_data_dir
                
                # Import and run the demo
                demo_path = os.path.join(os.path.dirname(__file__), demo_file)
                
                if not os.path.exists(demo_path):
                    print(f"❌ Demo file not found: {demo_path}")
                    return False
                
                # Load the demo module
                spec = importlib.util.spec_from_file_location(demo_name, demo_path)
                demo_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(demo_module)
                
                # Run the demo
                start_time = time.time()
                
                if hasattr(demo_module, 'main'):
                    demo_module.main()
                else:
                    print(f"❌ Demo {demo_name} does not have a main() function")
                    return False
                
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"✅ Demo {demo_name} completed successfully in {duration:.2f}s")
                self.test_results[demo_name] = {
                    'status': 'PASSED',
                    'duration': duration,
                    'error': None
                }
                return True
                
            except Exception as e:
                print(f"❌ Demo {demo_name} failed: {e}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                
                self.test_results[demo_name] = {
                    'status': 'FAILED',
                    'duration': time.time() - start_time if 'start_time' in locals() else 0,
                    'error': str(e)
                }
                return False
    
    def run_all_demos(self, config_file: str = "yaml/config-local.yaml", use_existing: bool = True) -> Dict:
        """Run all demos with professional testing practices"""
        print("🚀 PROFESSIONAL TEST RUNNER")
        print("=" * 80)
        print("Running all demos with professional testing practices:")
        print("  ✅ Temporary directories for test isolation")
        print("  ✅ Automatic cleanup after each test")
        print("  ✅ Professional logging and error handling")
        print("  ✅ Test result reporting")
        print("=" * 80)
        
        start_time = time.time()
        passed = 0
        failed = 0
        
        for demo_name in self.demos.keys():
            success = self.run_demo(demo_name, config_file, use_existing)
            if success:
                passed += 1
            else:
                failed += 1
            
            # Small delay between demos
            time.sleep(2)
        
        total_time = time.time() - start_time
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"Total demos: {len(self.demos)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average time per demo: {total_time/len(self.demos):.2f}s")
        
        print("\nDetailed Results:")
        for demo_name, result in self.test_results.items():
            status_icon = "✅" if result['status'] == 'PASSED' else "❌"
            print(f"  {status_icon} {demo_name}: {result['status']} ({result['duration']:.2f}s)")
            if result['error']:
                print(f"      Error: {result['error']}")
        
        print("\n" + "=" * 80)
        if failed == 0:
            print("🎉 ALL DEMOS PASSED!")
        else:
            print(f"⚠️ {failed} demo(s) failed. Check the output above for details.")
        
        return self.test_results
    
    def cleanup_all(self):
        """Clean up all test artifacts"""
        print("\n🧹 Performing global cleanup...")
        global_test_cleanup()
        print("✅ Global cleanup completed")

def main():
    """Main function for professional test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Professional Test Runner for Distributed Database Demos")
    parser.add_argument("--demo", help="Run specific demo (default: run all)")
    parser.add_argument("--config", default="yaml/config-local.yaml", help="Configuration file")
    parser.add_argument("--new-cluster", action="store_true", help="Create new cluster instead of using existing")
    parser.add_argument("--list", action="store_true", help="List all available demos")
    
    args = parser.parse_args()
    
    runner = ProfessionalTestRunner()
    
    if args.list:
        print("Available Demos:")
        for demo_name, info in runner.demos.items():
            print(f"  {demo_name:<25} - {info['description']}")
        return
    
    try:
        if args.demo:
            # Run specific demo
            success = runner.run_demo(args.demo, args.config, not args.new_cluster)
            if not success:
                sys.exit(1)
        else:
            # Run all demos
            results = runner.run_all_demos(args.config, not args.new_cluster)
            failed_count = sum(1 for r in results.values() if r['status'] == 'FAILED')
            if failed_count > 0:
                sys.exit(1)
    finally:
        # Always cleanup
        runner.cleanup_all()

if __name__ == "__main__":
    main() 