import time
import requests
import random
import psycopg2
from concurrent.futures import ThreadPoolExecutor

DB_DSN = "dbname=athena_db user=athena password=athena_secret_change_me host=localhost port=5432"
JAVA_API = "http://localhost:8080/api"
PYTHON_API = "http://localhost:8001/api/v1/credit-reports"

def simulate_app_traffic():
    print("1. Connecting to DB to fetch users...")
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()
    cur.execute("SELECT customer_id, national_id, first_name, last_name, mobile_number FROM customers LIMIT 200;")
    customers = cur.fetchall()
    conn.close()

    print(f"Loaded {len(customers)} customers for load test.")

    print("2. Authenticating via Admin API...")
    login_res = requests.post(f"{JAVA_API}/auth/admin/login", json={"username": "admin", "password": "admin", "totpCode": "123456"})
    token = login_res.json()["token"]
    java_headers = {"Authorization": f"Bearer {token}"}
    py_headers = {"X-Api-Key": "dev-key", "Content-Type": "application/json"}

    successes = 0
    failures = 0

    def simulate_user(cust):
        cid, nid, fn, ln, phone = cust
        local_success = 0
        local_fail = 0
        
        # 1. Dashboard read
        if requests.get(f"{JAVA_API}/v1/dashboard/stats", headers=java_headers).status_code == 200:
            local_success += 1
            
        time.sleep(random.uniform(0.1, 0.3))

        # 2. View Score History
        requests.get(f"{JAVA_API}/v1/credit/report/{cid}", headers=java_headers)

        # 3. Mass Request AI Scoring (Python API direct)
        py_payload = {
            "customer": {
                "nationalId": nid,
                "firstName": fn,
                "lastName": ln,
                "phone": phone
            },
            "creditReport": {
                "bureauName": random.choice(["TransUnion", "Metropol", "Equifax"]),
                "reportDate": "2026-02-21"
            }
        }
        rescore = requests.post(PYTHON_API, headers=py_headers, json=py_payload)
        if rescore.status_code == 200:
            local_success += 1
        else:
            local_fail += 1

        # 4. View Disputes
        if random.random() < 0.3:
            requests.get(f"{JAVA_API}/v1/disputes", headers=java_headers)

        return (local_success, local_fail)

    print("3. Bombarding APIs...")
    with ThreadPoolExecutor(max_workers=15) as executor:
        for s, f in executor.map(simulate_user, customers):
            successes += s
            failures += f

    print("\n✅ Simulation Complete!")
    print(f"Total API Successes: {successes}")
    print(f"Total API Failures: {failures}")

if __name__ == "__main__":
    simulate_app_traffic()
