#!/usr/bin/env python3
"""
Create demo users and setup relationships for UI testing
This script creates test users with friendships and posts
"""

import requests
import time
import json

API_BASE = "http://localhost:8370"

def create_user(username, email, password):
    """Register a new user and return their token and ID"""
    response = requests.post(
        f"{API_BASE}/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password
        }
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Created user: {username} (ID: {data['user_id']})")
        return data['access_token'], data['user_id']
    else:
        print(f"❌ Failed to create {username}: {response.text}")
        # Try login if user exists
        login_response = requests.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        if login_response.status_code == 200:
            data = login_response.json()
            print(f"✅ Logged in existing user: {username} (ID: {data['user_id']})")
            return data['access_token'], data['user_id']
        return None, None

def add_friend(token, user_id, friend_id):
    """Add a friend relationship"""
    response = requests.post(
        f"{API_BASE}/api/v1/users/{user_id}/friends/{friend_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        print(f"  ✅ Added friend: User {user_id} → User {friend_id}")
    else:
        print(f"  ⚠️  Friend relationship may already exist")

def create_post(token, content):
    """Create a post"""
    response = requests.post(
        f"{API_BASE}/api/v1/posts",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": content}
    )
    if response.status_code == 200:
        post = response.json()
        print(f"  ✅ Created post: '{content[:50]}...' (ID: {post['id']})")
        return post['id']
    else:
        print(f"  ❌ Failed to create post")
        return None

def main():
    print("=" * 80)
    print("🚀 CREATING DEMO USERS FOR NEWS FEED UI")
    print("=" * 80)
    
    # Create users
    print("\n📝 Step 1: Creating Users...")
    alice_token, alice_id = create_user("alice", "alice@demo.com", "alice123")
    bob_token, bob_id = create_user("bob", "bob@demo.com", "bob123")
    charlie_token, charlie_id = create_user("charlie", "charlie@demo.com", "charlie123")
    diana_token, diana_id = create_user("diana", "diana@demo.com", "diana123")
    
    print("\n🤝 Step 2: Creating Friend Relationships...")
    if all([alice_token, bob_token, charlie_token, diana_token]):
        # Alice friends with Bob and Charlie
        add_friend(alice_token, alice_id, bob_id)
        add_friend(alice_token, alice_id, charlie_id)
        
        # Bob friends with Alice and Diana
        add_friend(bob_token, bob_id, alice_id)
        add_friend(bob_token, bob_id, diana_id)
        
        # Charlie friends with Alice and Diana
        add_friend(charlie_token, charlie_id, alice_id)
        add_friend(charlie_token, charlie_id, diana_id)
        
        # Diana friends with Bob and Charlie
        add_friend(diana_token, diana_id, bob_id)
        add_friend(diana_token, diana_id, charlie_id)
        
        print("\n📝 Step 3: Creating Sample Posts...")
        
        # Alice's posts
        print(f"\nAlice creating posts...")
        create_post(alice_token, "Hello everyone! Alice here. Excited to join this social network! 🎉")
        create_post(alice_token, "Just finished reading a great book on microservices architecture. Highly recommend!")
        create_post(alice_token, "Anyone up for a virtual coffee chat this weekend? ☕")
        
        # Bob's posts
        print(f"\nBob creating posts...")
        create_post(bob_token, "Bob here! Working on some cool React projects today. Love the new hooks!")
        create_post(bob_token, "Pro tip: Always use proper error handling in your async functions 💡")
        create_post(bob_token, "Happy Friday everyone! What are your weekend plans?")
        
        # Charlie's posts
        print(f"\nCharlie creating posts...")
        create_post(charlie_token, "Charlie checking in! Just deployed my first microservices app 🚀")
        create_post(charlie_token, "Redis caching is a game changer for performance!")
        create_post(charlie_token, "Looking for recommendations on distributed systems books 📚")
        
        # Diana's posts
        print(f"\nDiana creating posts...")
        create_post(diana_token, "Diana here! Loving this news feed system architecture")
        create_post(diana_token, "Just learned about Celery for async task processing. Mind blown! 🤯")
        create_post(diana_token, "Weekend project: Building a real-time chat application")
        
        print("\n" + "=" * 80)
        print("✅ DEMO SETUP COMPLETE!")
        print("=" * 80)
        
        print("\n📱 UI TESTING INSTRUCTIONS:")
        print("1. Open http://localhost:3000 in your browser")
        print("\n2. Login with any of these users:")
        print("   • Username: alice    | Password: alice123    | ID:", alice_id)
        print("   • Username: bob      | Password: bob123      | ID:", bob_id)
        print("   • Username: charlie  | Password: charlie123  | ID:", charlie_id)
        print("   • Username: diana    | Password: diana123    | ID:", diana_id)
        
        print("\n3. Features to test:")
        print("   • 📰 View personalized news feed (you'll see posts from friends)")
        print("   • 📝 Create new posts")
        print("   • 👥 View friends list (click People icon)")
        print("   • ➕ Add more friends using their ID")
        print("   • 🔔 Check notifications (click Bell icon)")
        print("   • 🔄 Refresh feed for new posts")
        print("   • 🗑️ Delete your own posts")
        
        print("\n4. Friend relationships:")
        print("   • Alice ↔️ Bob, Charlie")
        print("   • Bob ↔️ Alice, Diana")
        print("   • Charlie ↔️ Alice, Diana")
        print("   • Diana ↔️ Bob, Charlie")
        
        print("\n5. Try this workflow:")
        print("   a. Login as Alice")
        print("   b. View feed (should see Bob's and Charlie's posts)")
        print("   c. Create a new post")
        print("   d. Logout and login as Bob")
        print("   e. Check if Alice's new post appears in feed")
        print("   f. Click refresh if needed")
        
        print("\n🎉 Enjoy exploring the News Feed System!")
        
    else:
        print("\n❌ Failed to create all users. Please check if services are running.")

if __name__ == "__main__":
    main()