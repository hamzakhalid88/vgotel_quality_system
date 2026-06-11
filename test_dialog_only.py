from database import Database
db = Database()
try:
    user_id = db.create_user({
        'username': 'test99',
        'password': 'pass123',
        'full_name': 'Test User',
        'email': 'test99@example.com',
        'role': 'viewer'
    })
    print(f"✅ User created with ID: {user_id}")
except Exception as e:
    print(f"❌ Failed: {e}")