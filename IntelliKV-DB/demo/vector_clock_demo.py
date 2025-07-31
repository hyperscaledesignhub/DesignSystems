#!/usr/bin/env python3
"""
Vector Clock Functionality Demo
Comprehensive demonstration of vector clock operations with validation

This demo shows:
1. Vector clock creation and basic operations
2. Increment operations
3. Merge operations  
4. Comparison operations (dominates, concurrent, equal)
5. Real-world scenarios with validation
"""

import time
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

# Import our vector clock implementation
from causal_consistency_lib import VectorClock, CausalVersionedValue

class VectorClockDemo:
    """Comprehensive vector clock demonstration with validation"""
    
    def __init__(self):
        self.test_results = []
        self.validation_errors = []
    
    def log_test(self, test_name: str, result: bool, details: str = ""):
        """Log test result with validation"""
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        self.test_results.append((test_name, result, details))
        
        if not result:
            self.validation_errors.append(f"{test_name}: {details}")
    
    def validate_vector_clock(self, vc: VectorClock, expected_clocks: Dict[str, int], test_name: str):
        """Validate vector clock state"""
        actual = vc.clocks
        if actual == expected_clocks:
            self.log_test(test_name, True, f"Expected: {expected_clocks}, Got: {actual}")
        else:
            self.log_test(test_name, False, f"Expected: {expected_clocks}, Got: {actual}")
    
    def validate_comparison(self, vc1: VectorClock, vc2: VectorClock, expected_result: str, test_name: str):
        """Validate vector clock comparison"""
        if expected_result == "dominates":
            # vc1 dominates vc2 means vc2 < vc1 (vc2 happens before vc1)
            result = vc2 < vc1
            self.log_test(test_name, result, f"{vc2} < {vc1} = {result} (vc1 dominates vc2)")
        elif expected_result == "concurrent":
            result = not (vc1 < vc2) and not (vc2 < vc1)
            self.log_test(test_name, result, f"{vc1} concurrent with {vc2} = {result}")
        elif expected_result == "equal":
            result = vc1 == vc2
            self.log_test(test_name, result, f"{vc1} == {vc2} = {result}")
    
    def demo_basic_operations(self):
        """Demo 1: Basic vector clock operations"""
        print("\n" + "="*60)
        print("DEMO 1: BASIC VECTOR CLOCK OPERATIONS")
        print("="*60)
        
        # Test 1: Create vector clock
        print("\n1. Creating vector clock for node 'alice'")
        vc_alice = VectorClock.create("alice")
        self.validate_vector_clock(vc_alice, {"alice": 0}, "Create vector clock")
        
        # Test 2: Increment operation
        print("\n2. Incrementing alice's clock")
        vc_alice = vc_alice.increment("alice")
        self.validate_vector_clock(vc_alice, {"alice": 1}, "Increment operation")
        
        # Test 3: Multiple increments
        print("\n3. Multiple increments")
        vc_alice = vc_alice.increment("alice")
        vc_alice = vc_alice.increment("alice")
        self.validate_vector_clock(vc_alice, {"alice": 3}, "Multiple increments")
        
        # Test 4: Create another node
        print("\n4. Creating vector clock for node 'bob'")
        vc_bob = VectorClock.create("bob")
        vc_bob = vc_bob.increment("bob")
        self.validate_vector_clock(vc_bob, {"bob": 1}, "Create and increment bob")
    
    def demo_merge_operations(self):
        """Demo 2: Vector clock merge operations"""
        print("\n" + "="*60)
        print("DEMO 2: VECTOR CLOCK MERGE OPERATIONS")
        print("="*60)
        
        # Setup initial clocks
        vc_alice = VectorClock.create("alice")
        vc_alice = vc_alice.increment("alice").increment("alice")  # alice: 2
        
        vc_bob = VectorClock.create("bob")
        vc_bob = vc_bob.increment("bob")  # bob: 1
        
        print(f"\nInitial clocks:")
        print(f"Alice: {vc_alice}")
        print(f"Bob: {vc_bob}")
        
        # Test 1: Merge bob into alice
        print("\n1. Merging bob's clock into alice's clock")
        vc_alice_merged = vc_alice.merge(vc_bob)
        expected = {"alice": 2, "bob": 1}
        self.validate_vector_clock(vc_alice_merged, expected, "Merge bob into alice")
        
        # Test 2: Merge alice into bob
        print("\n2. Merging alice's clock into bob's clock")
        vc_bob_merged = vc_bob.merge(vc_alice)
        expected = {"alice": 2, "bob": 1}
        self.validate_vector_clock(vc_bob_merged, expected, "Merge alice into bob")
        
        # Test 3: Verify both clocks are now equal
        print("\n3. Verifying clocks are equal after merge")
        self.validate_comparison(vc_alice_merged, vc_bob_merged, "equal", "Clocks equal after merge")
        
        # Test 4: Merge with different values
        print("\n4. Testing merge with different values")
        vc_charlie = VectorClock.create("charlie")
        vc_charlie = vc_charlie.increment("charlie").increment("charlie").increment("charlie")  # charlie: 3
        
        # Start with alice's merged clock (which has bob)
        vc_alice = vc_alice_merged.increment("alice")  # alice: 3, bob: 1
        vc_alice = vc_alice.merge(vc_charlie)
        expected = {"alice": 3, "bob": 1, "charlie": 3}
        self.validate_vector_clock(vc_alice, expected, "Merge with different values")
    
    def demo_comparison_operations(self):
        """Demo 3: Vector clock comparison operations"""
        print("\n" + "="*60)
        print("DEMO 3: VECTOR CLOCK COMPARISON OPERATIONS")
        print("="*60)
        
        # Test 1: Dominates relationship
        print("\n1. Testing dominates relationship")
        vc_old = VectorClock(clocks={"alice": 1, "bob": 1})
        vc_new = VectorClock(clocks={"alice": 2, "bob": 1})
        
        print(f"Old clock: {vc_old}")
        print(f"New clock: {vc_new}")
        self.validate_comparison(vc_new, vc_old, "dominates", "New clock dominates old clock")
        # The old clock is dominated by the new clock, so they are not concurrent
        # Instead of testing for concurrency, explicitly check that old < new (old is causally before new)
        result = vc_old < vc_new
        self.log_test("Old clock is causally before new clock", result, f"{vc_old} < {vc_new} = {result}")
        
        # Test 2: Concurrent clocks
        print("\n2. Testing concurrent clocks")
        vc_a = VectorClock(clocks={"alice": 2, "bob": 1})
        vc_b = VectorClock(clocks={"alice": 1, "bob": 2})
        
        print(f"Clock A: {vc_a}")
        print(f"Clock B: {vc_b}")
        self.validate_comparison(vc_a, vc_b, "concurrent", "Clocks are concurrent")
        
        # Test 3: Equal clocks
        print("\n3. Testing equal clocks")
        vc_same1 = VectorClock(clocks={"alice": 2, "bob": 1})
        vc_same2 = VectorClock(clocks={"alice": 2, "bob": 1})
        
        print(f"Clock 1: {vc_same1}")
        print(f"Clock 2: {vc_same2}")
        self.validate_comparison(vc_same1, vc_same2, "equal", "Clocks are equal")
        
        # Test 4: Complex domination
        print("\n4. Testing complex domination")
        vc_complex1 = VectorClock(clocks={"alice": 3, "bob": 2, "charlie": 1})
        vc_complex2 = VectorClock(clocks={"alice": 2, "bob": 1})
        
        print(f"Complex clock 1: {vc_complex1}")
        print(f"Complex clock 2: {vc_complex2}")
        self.validate_comparison(vc_complex1, vc_complex2, "dominates", "Complex clock 1 dominates clock 2")
    
    def demo_real_world_scenario(self):
        """Demo 4: Real-world scenario with multiple nodes"""
        print("\n" + "="*60)
        print("DEMO 4: REAL-WORLD SCENARIO - MULTI-NODE OPERATIONS")
        print("="*60)
        
        # Scenario: Three nodes (alice, bob, charlie) working on a shared document
        
        print("\n📝 Scenario: Three users editing a shared document")
        print("   - Alice writes: 'Hello World'")
        print("   - Bob writes: 'Hello Universe'") 
        print("   - Charlie writes: 'Hello Galaxy'")
        print("   - All operations happen concurrently")
        
        # Step 1: Initial state
        print("\n1. Initial state - all nodes start with empty clocks")
        vc_alice = VectorClock.create("alice")
        vc_bob = VectorClock.create("bob")
        vc_charlie = VectorClock.create("charlie")
        
        self.validate_vector_clock(vc_alice, {"alice": 0}, "Alice initial")
        self.validate_vector_clock(vc_bob, {"bob": 0}, "Bob initial")
        self.validate_vector_clock(vc_charlie, {"charlie": 0}, "Charlie initial")
        
        # Step 2: Concurrent operations
        print("\n2. Concurrent operations - each node writes independently")
        vc_alice = vc_alice.increment("alice")  # Alice writes "Hello World"
        vc_bob = vc_bob.increment("bob")        # Bob writes "Hello Universe"
        vc_charlie = vc_charlie.increment("charlie")  # Charlie writes "Hello Galaxy"
        
        self.validate_vector_clock(vc_alice, {"alice": 1}, "Alice after write")
        self.validate_vector_clock(vc_bob, {"bob": 1}, "Bob after write")
        self.validate_vector_clock(vc_charlie, {"charlie": 1}, "Charlie after write")
        
        # Step 3: Verify they are concurrent
        print("\n3. Verifying operations are concurrent")
        self.validate_comparison(vc_alice, vc_bob, "concurrent", "Alice and Bob concurrent")
        self.validate_comparison(vc_bob, vc_charlie, "concurrent", "Bob and Charlie concurrent")
        self.validate_comparison(vc_alice, vc_charlie, "concurrent", "Alice and Charlie concurrent")
        
        # Step 4: Gossip/sync between nodes
        print("\n4. Gossip/sync - nodes learn about each other")
        vc_alice = vc_alice.merge(vc_bob).merge(vc_charlie)
        vc_bob = vc_bob.merge(vc_alice).merge(vc_charlie)
        vc_charlie = vc_charlie.merge(vc_alice).merge(vc_bob)
        
        expected_merged = {"alice": 1, "bob": 1, "charlie": 1}
        self.validate_vector_clock(vc_alice, expected_merged, "Alice after merge")
        self.validate_vector_clock(vc_bob, expected_merged, "Bob after merge")
        self.validate_vector_clock(vc_charlie, expected_merged, "Charlie after merge")
        
        # Step 5: Verify they are now equal
        print("\n5. Verifying all clocks are equal after sync")
        self.validate_comparison(vc_alice, vc_bob, "equal", "Alice and Bob equal after sync")
        self.validate_comparison(vc_bob, vc_charlie, "equal", "Bob and Charlie equal after sync")
        
        # Step 6: New operation after sync
        print("\n6. New operation after sync - Alice writes again")
        vc_alice = vc_alice.increment("alice")  # Alice writes "Hello World 2.0"
        
        expected_alice_new = {"alice": 2, "bob": 1, "charlie": 1}
        self.validate_vector_clock(vc_alice, expected_alice_new, "Alice after new write")
        
        # Step 7: Verify domination
        print("\n7. Verifying Alice's new clock dominates others")
        self.validate_comparison(vc_alice, vc_bob, "dominates", "Alice dominates Bob after new write")
        self.validate_comparison(vc_alice, vc_charlie, "dominates", "Alice dominates Charlie after new write")
    
    def demo_conflict_resolution(self):
        """Demo 5: Conflict resolution with vector clocks"""
        print("\n" + "="*60)
        print("DEMO 5: CONFLICT RESOLUTION WITH VECTOR CLOCKS")
        print("="*60)
        
        print("\n🔧 Scenario: Conflict resolution when concurrent operations occur")
        
        # Create conflicting values
        vc_alice = VectorClock.create("alice")
        vc_alice = vc_alice.increment("alice")
        
        vc_bob = VectorClock.create("bob")
        vc_bob = vc_bob.increment("bob")
        
        # Create causal values with same key but different values
        value_alice = CausalVersionedValue("Hello from Alice", vc_alice, "alice")
        value_bob = CausalVersionedValue("Hello from Bob", vc_bob, "bob")
        
        print(f"\nConflicting values:")
        print(f"Alice: {value_alice}")
        print(f"Bob: {value_bob}")
        
        # Test 1: Verify they are concurrent
        print("\n1. Verifying values are concurrent")
        self.validate_comparison(vc_alice, vc_bob, "concurrent", "Alice and Bob clocks are concurrent")
        
        # Test 2: Simulate conflict resolution (last-write-wins by timestamp)
        print("\n2. Simulating conflict resolution (last-write-wins)")
        if value_alice.creation_time > value_bob.creation_time:
            winner = value_alice
            loser = value_bob
            print(f"   Winner: Alice (newer timestamp)")
        else:
            winner = value_bob
            loser = value_alice
            print(f"   Winner: Bob (newer timestamp)")
        
        print(f"   Winner: {winner}")
        print(f"   Loser: {loser}")
        
        # Test 3: Verify winner dominates after resolution
        print("\n3. Verifying winner dominates after resolution")
        # In a real system, the winner would have its clock incremented
        winner_clock = winner.vector_clock.increment(winner.node_id)
        # Also merge the loser's clock to ensure proper domination
        winner_clock = winner_clock.merge(loser.vector_clock)
        self.validate_comparison(winner_clock, loser.vector_clock, "dominates", "Winner dominates loser after resolution")
    
    def demo_edge_cases(self):
        """Demo 6: Edge cases and validation"""
        print("\n" + "="*60)
        print("DEMO 6: EDGE CASES AND VALIDATION")
        print("="*60)
        
        # Test 1: Empty vector clock
        print("\n1. Testing empty vector clock")
        vc_empty = VectorClock()
        self.validate_vector_clock(vc_empty, {}, "Empty vector clock")
        
        # Test 2: Vector clock with missing nodes
        print("\n2. Testing vector clock with missing nodes")
        vc_partial = VectorClock(clocks={"alice": 2, "bob": 1})
        vc_complete = VectorClock(clocks={"alice": 2, "bob": 1, "charlie": 0})
        
        print(f"Partial: {vc_partial}")
        print(f"Complete: {vc_complete}")
        self.validate_comparison(vc_complete, vc_partial, "dominates", "Complete dominates partial")
        
        # Test 3: Vector clock with zero values
        print("\n3. Testing vector clock with zero values")
        vc_zeros = VectorClock(clocks={"alice": 0, "bob": 0, "charlie": 0})
        vc_ones = VectorClock(clocks={"alice": 1, "bob": 1, "charlie": 1})
        
        self.validate_comparison(vc_ones, vc_zeros, "dominates", "Ones dominate zeros")
        
        # Test 4: Large numbers
        print("\n4. Testing vector clock with large numbers")
        vc_large = VectorClock(clocks={"alice": 1000, "bob": 500, "charlie": 750})
        vc_small = VectorClock(clocks={"alice": 999, "bob": 499, "charlie": 749})
        
        self.validate_comparison(vc_large, vc_small, "dominates", "Large dominates small")
    
    def run_all_demos(self):
        """Run all vector clock demos"""
        print("🚀 VECTOR CLOCK FUNCTIONALITY DEMO")
        print("="*60)
        print("This demo validates all core vector clock operations")
        print("Each test includes proper validation and error checking")
        
        try:
            self.demo_basic_operations()
            self.demo_merge_operations()
            self.demo_comparison_operations()
            self.demo_real_world_scenario()
            self.demo_conflict_resolution()
            self.demo_edge_cases()
            
            # Summary
            print("\n" + "="*60)
            print("DEMO SUMMARY")
            print("="*60)
            
            total_tests = len(self.test_results)
            passed_tests = sum(1 for _, result, _ in self.test_results if result)
            failed_tests = total_tests - passed_tests
            
            print(f"Total tests: {total_tests}")
            print(f"Passed: {passed_tests} ✅")
            print(f"Failed: {failed_tests} ❌")
            
            if failed_tests == 0:
                print("\n🎉 ALL TESTS PASSED! Vector clock implementation is working correctly.")
            else:
                print(f"\n⚠️ {failed_tests} tests failed. Check the errors above.")
                for error in self.validation_errors:
                    print(f"   - {error}")
            
            return failed_tests == 0
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            return False

def main():
    """Main function to run the vector clock demo"""
    demo = VectorClockDemo()
    success = demo.run_all_demos()
    
    if success:
        print("\n✅ Vector clock demo completed successfully!")
        print("   All core functionality is working correctly.")
        print("   The implementation handles:")
        print("   - Basic operations (create, increment)")
        print("   - Merge operations")
        print("   - Comparison operations (dominates, concurrent, equal)")
        print("   - Real-world scenarios")
        print("   - Conflict resolution")
        print("   - Edge cases")
    else:
        print("\n❌ Vector clock demo failed!")
        print("   Please check the implementation for issues.")
    
    return success

if __name__ == "__main__":
    main() 