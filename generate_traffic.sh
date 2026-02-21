#!/bin/bash
# Simulate traffic through the Athena portals to generate Grafana metrics

echo "1. Getting Admin Token..."
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r .token)

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "Login failed. Java service might still be booting."
    exit 1
fi

echo "2. Hitting Dashboard Stats..."
for i in {1..10}; do
    curl -s http://localhost:8080/api/v1/dashboard/stats -H "Authorization: Bearer $TOKEN" >/dev/null
    sleep 0.1
done

echo "3. Browsing Customers..."
for i in {1..20}; do
    curl -s "http://localhost:8080/api/v1/customers/search?q=KE" -H "Authorization: Bearer $TOKEN" >/dev/null
    sleep 0.1
done

echo "4. Viewing Credit Reports & Triggering Scores..."
# Pick 10 random seeded customers
for id in 5 12 45 88 102 230 445 780 910 999; do
    echo "   -> Customer $id"
    # View report
    curl -s http://localhost:8080/api/v1/credit/report/$id -H "Authorization: Bearer $TOKEN" >/dev/null
    # Trigger fresh scoring run
    curl -s -X POST http://localhost:8080/api/v1/credit/score/$id/trigger \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"reason": "Manual review"}' >/dev/null
    # Get history
    curl -s http://localhost:8080/api/v1/credit/score/$id/history -H "Authorization: Bearer $TOKEN" >/dev/null
    sleep 0.5
done

echo "5. Viewing Disputes..."
for i in {1..5}; do
    curl -s http://localhost:8080/api/v1/disputes -H "Authorization: Bearer $TOKEN" >/dev/null
    sleep 0.2
done

echo "✅ Traffic simulation complete! Check Grafana dashboards at http://localhost:3000"
