#!/usr/bin/env python3
import requests
import json
import time

# Login
login_resp = requests.post('http://localhost:8000/login', json={
    'email': 'finaltest2@example.com',
    'password': 'testpass123'
})
token = login_resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Send test email
email_resp = requests.post('http://localhost:8000/emails', json={
    'to_recipients': ['demo@example.com'],
    'subject': 'Customer Demo Email',
    'body': 'This is a test email for the customer demonstration. It should be searchable in Elasticsearch!'
}, headers=headers)

if email_resp.status_code == 200:
    email_data = email_resp.json()
    print(f"✅ Email sent: {email_data['subject']} (ID: {email_data['id']})")
    
    # Wait a moment for indexing
    print("⏳ Waiting 3 seconds for Elasticsearch indexing...")
    time.sleep(3)
    
    # Test search
    search_resp = requests.post('http://localhost:8000/search', json={
        'query': 'Customer Demo'
    }, headers=headers)
    
    search_data = search_resp.json()
    print(f"🔍 Search results: Found {search_data.get('total', 0)} emails")
    for result in search_data.get('results', []):
        print(f"   - {result.get('subject', 'No subject')}")
        
    if search_data.get('total', 0) == 0:
        print("❌ Search returned 0 results - checking if email exists in database...")
        
        # Check if email exists via GET
        emails_resp = requests.get('http://localhost:8000/emails', headers=headers)
        emails = emails_resp.json()
        print(f"📧 Found {len(emails)} emails in database:")
        for email in emails:
            print(f"   - {email['subject']}")
            
        # Try manual reindex
        print("🔧 Trying manual reindex...")
        if emails:
            reindex_resp = requests.post(f'http://localhost:8000/search/reindex', headers=headers)
            print(f"Reindex response: {reindex_resp.status_code}")
            
            # Search again after reindex
            time.sleep(2)
            search_resp2 = requests.post('http://localhost:8000/search', json={
                'query': 'Customer Demo'
            }, headers=headers)
            search_data2 = search_resp2.json()
            print(f"🔍 Search after reindex: Found {search_data2.get('total', 0)} emails")

else:
    print(f"❌ Email sending failed: {email_resp.status_code}")
    print(email_resp.text)