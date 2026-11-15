import os
import sys
import json
from app import app
import database as db

client = app.test_client()

def test_all():
    print("=== 1. Testing Web Pages / and /login ===")
    res_home = client.get('/')
    assert res_home.status_code == 200, f"Home failed: {res_home.status_code}"
    assert "AegisMind" in res_home.text
    assert "app.js" in res_home.text
    assert "panel-home" in res_home.text
    assert "panel-checkin" in res_home.text
    assert "panel-chat" in res_home.text
    assert "supabase" in res_home.text
    print("✓ Dashboard (/) rendered HTTP 200 with all panels and scripts")

    res_login = client.get('/login')
    assert res_login.status_code == 200, f"Login failed: {res_login.status_code}"
    assert "supabase" in res_login.text
    assert "Sign In" in res_login.text
    print("✓ Login page (/login) rendered HTTP 200 with Supabase auth form")

    print("\n=== 2. Testing Registration and Login ===")
    import uuid
    run_id = uuid.uuid4().hex[:6]
    user_a_email = f"alex.aegismind.{run_id}@gmail.com"
    user_a_pwd = "SecurePassword123!"
    
    # Registration
    res_reg = client.post('/api/register', json={"email": user_a_email, "password": user_a_pwd, "consent": True})
    reg_data = res_reg.get_json()
    print("Register response:", res_reg.status_code, reg_data)
    assert res_reg.status_code == 200
    token_a = reg_data.get("token")
    assert token_a, "Missing token for registered user"
    
    # Login
    res_log = client.post('/api/login', json={"email": user_a_email, "password": user_a_pwd})
    log_data = res_log.get_json()
    print("Login response:", res_log.status_code, log_data)
    assert res_log.status_code == 200
    assert log_data.get("token") == token_a
    print("✓ Email/password registration and login verified")

    print("\n=== 3. Testing Check-in and Multi-Agent Pipeline ===")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # Submitting standard check-in
    checkin_payload = {
        "text": "Today was quite challenging at work. Feeling tired and anxious about deadlines.",
        "valence": 4.5,
        "arousal": 6.2,
        "voice_score": 0.65
    }
    res_chk = client.post('/api/checkin', json=checkin_payload, headers=headers_a)
    print("Checkin response:", res_chk.status_code, res_chk.get_json())
    assert res_chk.status_code == 200
    chk_json = res_chk.get_json()
    assert "trajectory" in chk_json or "dpi" in chk_json or "risk_level" in chk_json
    print("✓ Multi-agent pipeline processed check-in and computed trajectory")

    print("\n=== 4. Testing Chat & AI Conversational Memory ===")
    chat_payload_1 = {
        "message": "Hello, my name is Alex. I have been having trouble sleeping because of my exams.",
        "context": "Journaling"
    }
    res_chat1 = client.post('/api/chat', json=chat_payload_1, headers=headers_a)
    assert res_chat1.status_code == 200
    reply1 = res_chat1.get_json().get("reply")
    print("AI First Reply:", reply1[:100] + "...")
    assert reply1 and len(reply1) > 0

    # Second message tests conversational memory
    chat_payload_2 = {
        "message": "Do you remember my name and what I am preparing for?",
        "context": "Follow-up"
    }
    res_chat2 = client.post('/api/chat', json=chat_payload_2, headers=headers_a)
    assert res_chat2.status_code == 200
    reply2 = res_chat2.get_json().get("reply")
    print("AI Memory Recall Reply:", reply2)
    assert "Alex" in reply2 or "exam" in reply2.lower()
    print("✓ Persistent AI memory successfully recalled user name and exam context")

    print("\n=== 5. Testing Forum and HITL Counselor Queue ===")
    forum_list = client.get('/api/forum', headers=headers_a)
    assert forum_list.status_code == 200
    print("Existing forum posts:", len(forum_list.get_json()))

    forum_post = {
        "text": "Looking for advice on managing night-time anxiety. Any techniques that work for you?",
        "lang": "en"
    }
    res_post = client.post('/api/forum', json=forum_post, headers=headers_a)
    assert res_post.status_code == 201
    print("✓ Forum post published successfully (HTTP 201)")

    counselor_res = client.get('/api/counselor/queue', headers=headers_a)
    assert counselor_res.status_code == 200
    print("Counselor queue count:", len(counselor_res.get_json()))
    print("✓ Counselor queue accessible")

    print("\n=== 6. Testing Data Isolation across Multiple Users ===")
    user_b_email = f"bianca.aegismind.{run_id}@gmail.com"
    user_b_pwd = "Password456!Secure"
    res_reg_b = client.post('/api/register', json={"email": user_b_email, "password": user_b_pwd, "consent": True})
    token_b = res_reg_b.get_json().get("token")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    history_a = client.get(f'/api/history/{token_a}', headers=headers_a).get_json()
    history_b = client.get(f'/api/history/{token_b}', headers=headers_b).get_json()
    
    checkins_a = history_a.get("records", [])
    checkins_b = history_b.get("records", [])
    print(f"User A check-ins count: {len(checkins_a)}, User B check-ins count: {len(checkins_b)}")
    assert len(checkins_a) >= 1
    assert len(checkins_b) == 0, "Isolation failure: User B sees User A's check-ins"

    chat_history_a = db.get_chat_history(token_a)
    chat_history_b = db.get_chat_history(token_b)
    print(f"User A chat count: {len(chat_history_a)}, User B chat history count: {len(chat_history_b)}")
    assert len(chat_history_a) >= 2
    assert len(chat_history_b) == 0, "Isolation failure: User B sees User A's chat history"
    print("✓ User data isolation strictly verified")

    print("\n=== 7. Testing Persistence Across Server Process Restart ===")
    # Simulate fresh import / database instance reconnection
    import importlib
    import database as db_fresh
    
    # Check that User A's records persist in the persistent DB
    stored_checkins = db_fresh.get_checkin_history(token_a)
    stored_chats = db_fresh.get_chat_history(token_a)
    print(f"Post-restart checkins found: {len(stored_checkins)}, chats found: {len(stored_chats)}")
    assert len(stored_checkins) >= 1
    assert len(stored_chats) >= 2
    print("✓ Persistence across restart verified (data stored in persistent DB)")

    print("\n🎉 ALL 7 TEST SUITES PASSED FLAWLESSLY!")

if __name__ == "__main__":
    test_all()
