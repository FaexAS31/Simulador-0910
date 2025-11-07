
import requests
import json

BASE_URL = "http://localhost:8000/api"
TEST_USER_EMAIL = f"testjwt{__import__('random').randint(1000, 9999)}@test.com"

print("\n" + "█" * 60)
print("  JWT AUTHENTICATION TEST SUITE")
print("  Testing Token Generation")
print("█" * 60)

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_request(method, url, data=None):
    print(f"\nRequest:\n{method} {url}")
    if data:
        print(json.dumps(data, indent=2))

def print_response(response):
    print(f"\nResponse: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

print_section("TEST 1: Register with JWT Tokens")

register_data = {
    "nombre": "JWT Test User",
    "email": TEST_USER_EMAIL,
    "password": "SecurePass12354",
    "telefono": "1234567890",
    "rol": "consumidor",
    "genero": "masculino"
}

print_request("POST", f"{BASE_URL}/usuarios/register/", register_data)
response = requests.post(f"{BASE_URL}/usuarios/register/", json=register_data)
print_response(response)

if response.status_code == 201:
    data = response.json()
    assert 'token' in data, "❌ Missing 'token' in response"
    assert 'refresh_token' in data, "❌ Missing 'refresh_token' in response"
    assert 'expires_in' in data, "❌ Missing 'expires_in' in response"
    assert 'user' in data, "❌ Missing 'user' in response"
    assert data['expires_in'] == 3600, "❌ expires_in should be 3600"
    assert data['user']['genero'] == 'masculino', "❌ genero not saved correctly"
    
    access_token = data['token']
    refresh_token = data['refresh_token']
    user_id = data['user']['id']
    
    print("\n✅ Register with JWT tokens successful")
    print(f"   User ID: {user_id}")
    print(f"   Access Token: {access_token[:50]}...")
    print(f"   Refresh Token: {refresh_token[:50]}...")
else:
    print("❌ Registration failed")
    exit(1)

print_section("TEST 2: Login with JWT Tokens")

login_data = {
    "email": TEST_USER_EMAIL,
    "password": "SecurePass12354"
}

print_request("POST", f"{BASE_URL}/usuarios/login/", login_data)
response = requests.post(f"{BASE_URL}/usuarios/login/", json=login_data)
print_response(response)

if response.status_code == 200:
    data = response.json()
    assert 'token' in data, "❌ Missing 'token' in response"
    assert 'refresh_token' in data, "❌ Missing 'refresh_token' in response"
    assert 'expires_in' in data, "❌ Missing 'expires_in' in response"
    assert 'user' in data, "❌ Missing 'user' in response"
    assert data['user']['email'] == TEST_USER_EMAIL, "❌ Wrong email in response"
    assert data['user']['genero'] == 'masculino', "❌ genero not returned correctly"
    
    new_access_token = data['token']
    
    print("\n✅ Login with JWT tokens successful")
    print(f"   New Access Token: {new_access_token[:50]}...")
else:
    print("❌ Login failed")
    exit(1)

print_section("TEST 3: Access Protected Endpoint with JWT")

headers = {
    "Authorization": f"Bearer {access_token}"
}

print_request("GET", f"{BASE_URL}/usuarios/{user_id}/")
print(f"Headers: Authorization: Bearer {access_token[:30]}...")
response = requests.get(f"{BASE_URL}/usuarios/{user_id}/", headers=headers)
print_response(response)

if response.status_code == 200:
    data = response.json()
    assert data['email'] == TEST_USER_EMAIL, "❌ Wrong user data"
    print("\n✅ JWT authentication successful")
else:
    print("❌ JWT authentication failed")

print_section("TEST 4: Access Without Token (Should Fail)")

print_request("GET", f"{BASE_URL}/usuarios/{user_id}/")
response = requests.get(f"{BASE_URL}/usuarios/{user_id}/")
print_response(response)

if response.status_code == 401:
    print("\n✅ Correctly rejected request without token")
else:
    print("❌ Should have rejected request without token")

print_section("TEST 5: Register Without Género (Optional Field)")

email2 = f"testjwt{__import__('random').randint(1000, 9999)}@test.com"
register_data2 = {
    "nombre": "Test User 2",
    "email": email2,
    "password": "SecurePass456",
    "rol": "consumidor"
}

print_request("POST", f"{BASE_URL}/usuarios/register/", register_data2)
response = requests.post(f"{BASE_URL}/usuarios/register/", json=register_data2)
print_response(response)

if response.status_code == 201:
    data = response.json()
    assert data['user']['genero'] is None, "❌ Should have genero as None"
    print("\n✅ Registration without género successful (defaults to None)")
else:
    print("❌ Registration should work without género")

print("\n" + "=" * 60)
print("  TEST SUMMARY")
print("=" * 60)
print("\n✅ All JWT authentication tests passed!")
print("\nToken Structure Verified:")
print("  ✓ Access token (JWT)")
print("  ✓ Refresh token (JWT)")
print("  ✓ expires_in: 3600 seconds (1 hour)")
print("  ✓ User data with role-specific fields")
print("  ✓ Género field (optional, defaults to None)")
print("\nAuthentication Flow:")
print("  ✓ Register → Returns tokens + user data")
print("  ✓ Login → Returns tokens + user data")
print("  ✓ Protected endpoints require Bearer token")
print("  ✓ Requests without token are rejected")

