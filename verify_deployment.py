import requests
import time

BASE_URL = "https://application-monitoring.onrender.com"

# Potential Admin Credentials
ADMIN_OPTIONS = [
    ("admin@monitoring.bj", "admin2026!"),
    ("admin@iot.com", "admin123")
]

def test_deployment():
    print(f"--- Testing Deployment at {BASE_URL} ---")
    
    # 1. Test Registration (Check if API + DB works)
    test_email = f"deploy_{int(time.time())}@testing.com"
    test_serial = f"SIM-{int(time.time()) % 1000:03d}"
    print(f"\n[1] Testing Registration for {test_email} with serial {test_serial}...")
    try:
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": test_email,
            "password": "password123",
            "full_name": "Deploy Test",
            "device_serial": test_serial
        }, timeout=20)
        
        if reg_resp.status_code == 201:
            print("[OK] Registration Successful")
            user_data = reg_resp.json()
            user_device_id = user_data.get('device_id')
            print(f"     Device ID: {user_device_id}")
        else:
            print(f"[FAIL] Registration Failed: {reg_resp.status_code} - {reg_resp.text}")
            return
    except Exception as e:
        print(f"[ERROR] Connection Error: {e}")
        return

    # 2. Test Login as the new user
    print("\n[2] Testing Login as the new user...")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": "password123"
    }, timeout=15)
    
    if login_resp.status_code == 200:
        print("[OK] Login Successful")
        user_token = login_resp.json()["access_token"]
    else:
        print(f"[FAIL] Login Failed: {login_resp.status_code} - {login_resp.text}")
        return

    # 3. Test Double Registration (Uniqueness)
    print("\n[3] Testing Uniqueness Constraint (Same Serial)...")
    reg_resp_2 = requests.post(f"{BASE_URL}/auth/register", json={
        "email": f"other_{int(time.time())}@testing.com",
        "password": "password123",
        "full_name": "Other User",
        "device_serial": test_serial
    }, timeout=15)
    
    if reg_resp_2.status_code == 400:
        print(f"[OK] Correctly rejected: {reg_resp_2.json().get('detail')}")
    else:
        print(f"[FAIL] Double registration NOT rejected: {reg_resp_2.status_code}")

    # 4. Test Isolation
    print("\n[4] Testing Data Isolation (X-Account Access)...")
    # Try to access device 0 or 1 (likely existing)
    for tid in [0, 1]:
        if tid == user_device_id: continue
        iso_resp = requests.get(f"{BASE_URL}/devices/{tid}", headers={
            "Authorization": f"Bearer {user_token}"
        }, timeout=15)
        if iso_resp.status_code == 403:
            print(f"[OK] Blocked access to Device {tid} (403 Forbidden)")
        elif iso_resp.status_code == 200:
            print(f"[CRITICAL] Security Leak: Read access to Device {tid} granted!")
        else:
            print(f"[INFO] Device {tid} Access Code: {iso_resp.status_code}")

    # 5. Try Admin Login (Fallbacks)
    print("\n[5] Testing Admin Credentials...")
    for email, pwd in ADMIN_OPTIONS:
        print(f"   Trying {email}...")
        try:
            adm_resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": email,
                "password": pwd
            }, timeout=15)
            if adm_resp.status_code == 200:
                print(f"   [OK] Admin Login Success with {email}")
                break
        except: pass
    else:
        print("   [INFO] No default admin found. (Admin might not be seeded)")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    test_deployment()
