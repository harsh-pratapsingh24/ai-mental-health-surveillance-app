"""Test script for AegisMind Flask App""" #import the libraries
from app import app, get_user_profile
import json

print('=== Testing AegisMind Flask App ===')
print()

client = app.test_client()

# Test 1: Home route
print('1. Testing / route...')
r = client.get('/')
print(f'   Status: {r.status_code} (Expected: 200)')

# Test 2: Health route
print('2. Testing /health route...')
r = client.get('/health')
print(f'   Status: {r.status_code} (Expected: 200)')
data = r.get_json()
print(f'   Status field: {data.get("status")}')

# Test 3: Login page
print('3. Testing /login route...')
r = client.get('/login')
print(f'   Status: {r.status_code} (Expected: 200)')

# Test 4: Register endpoint (anonymous)
print('4. Testing /api/register (anonymous)...')
r = client.post('/api/register', json={'consent': True})
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    data = r.get_json()
    print(f'   Token: {data.get("token", "N/A")[:8]}...')
    print(f'   Alias: {data.get("alias", "N/A")}')

# Test 5: Login endpoint (anonymous)
print('5. Testing /api/login (anonymous with token)...')
token = 'ANON1234567890ABCD'  # 16 chars
r = client.post('/api/login', json={'token': token})
print(f'   Status: {r.status_code}')

# Test 6: Checkin endpoint
print('6. Testing /api/checkin (with anonymous token)...')
r = client.post('/api/checkin', json={
    'token': 'ANON',
    'text': 'I am feeling good today',
    'valence': 7,
    'arousal': 5,
    'voice_score': 0.8
})
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    data = r.get_json()
    print(f'   Risk level: {data.get("trajectory", {}).get("risk_level", "N/A")}')
    print(f'   DPI: {data.get("trajectory", {}).get("dpi", "N/A")}')

# Test 7: Chat endpoint
print('7. Testing /api/chat...')
r = client.post('/api/chat', json={
    'token': 'ANON',
    'message': 'I feel anxious',
    'lang': 'en'
})
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    data = r.get_json()
    reply = data.get('reply', 'N/A')
    print(f'   Reply: {reply[:50]}...')
    print(f'   Is crisis: {data.get("is_crisis", False)}')

# Test 8: Forum endpoint
print('8. Testing /api/forum...')
r = client.get('/api/forum')
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    data = r.get_json()
    print(f'   Posts count: {len(data.get("posts", []))}')

# Test 9: Profile endpoint
print('9. Testing /api/profile/...')
r = client.get('/api/profile/ANON1234567890ABCD')
print(f'   Status: {r.status_code}')

# Test 10: Counselor queue (without auth key - should fail)
print('10. Testing /api/counselor/queue (no auth)...')
r = client.get('/api/counselor/queue')
print(f'   Status: {r.status_code}')

# Test 11: Forum post creation
print('11. Testing /api/forum POST...')
r = client.post('/api/forum', json={
    'text': 'Hello world, this is a test forum post.',
    'lang': 'en'
})
print(f'   Status: {r.status_code}')
if r.status_code == 201:
    data = r.get_json()
    print(f'   Post ID: {data.get("id", "N/A")[:8]}...')
    print(f'   Alias: {data.get("alias", "N/A")}')

# Test 12: Checkin with crisis text
print('12. Testing /api/checkin with crisis text...')
r = client.post('/api/checkin', json={
    'token': 'ANON',
    'text': 'I want to die and end it all',
    'valence': 2,
    'arousal': 9,
    'voice_score': 0.3
})
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    data = r.get_json()
    print(f'   Status: {data.get("status")}')
    print(f'   Agent: {data.get("agent_action", {}).get("agent", "N/A")}')

print()
print('=== All basic tests completed ===')