-- ============================================================
-- Athena Credit Score – Synthetic Data Seed (1000 Customers)
-- Matches actual DB schema as of 2026-02-20
-- ============================================================

-- 1. Customers
INSERT INTO customers (
    national_id, first_name, last_name, mobile_number, email,
    date_of_birth, gender, county, region,
    verification_status, crb_consent, credit_score, created_at
)
SELECT
    'KE' || LPAD(n::TEXT, 8, '0'),
    (ARRAY['James','Mary','John','Patricia','Robert','Linda','Michael','Barbara','William','Elizabeth','David','Jennifer','Richard','Maria','Joseph','Susan','Thomas','Margaret','Charles','Dorothy'])[1 + (n % 20)],
    (ARRAY['Kamau','Wanjiru','Omondi','Achieng','Mutua','Njeri','Otieno','Wangari','Mwangi','Chebet','Kimani','Auma','Kiprotich','Nyambura','Githae','Wairimu','Kariuki','Moraa','Ndegwa','Adhiambo'])[1 + ((n*7) % 20)],
    '+2547' || LPAD((10000000 + n*97)::TEXT, 8, '0'),
    'user' || n || '@athena-test.co.ke',
    NOW() - INTERVAL '1 year' * (20 + (n % 40)),
    CASE WHEN n % 2 = 0 THEN 'M' ELSE 'F' END,
    (ARRAY['Nairobi','Mombasa','Kisumu','Nakuru','Eldoret','Thika','Malindi','Kitale','Garissa','Kakamega'])[1 + (n % 10)],
    (ARRAY['Nairobi','Coast','Nyanza','Rift Valley','Central','Eastern','Western','North Eastern'])[1 + (n % 8)],
    'VERIFIED',
    true,
    300 + (n * 173 % 551),
    NOW() - INTERVAL '1 day' * (1 + n % 730)
FROM generate_series(1, 1000) AS n;

-- 2. Loans (3 per customer)
INSERT INTO loans (
    customer_id, principal_amount, interest_rate,
    tenure_months, disbursement_date, maturity_date, status
)
SELECT
    c.customer_id,
    5000 + ((c.customer_id * s.n * 37) % 195000),
    0.125 + ((c.customer_id * 3) % 13) * 0.01,
    (ARRAY[3,6,9,12,18,24])[1 + ((c.customer_id + s.n) % 6)],
    (NOW() - INTERVAL '1 day' * (30 + ((c.customer_id * s.n * 13) % 700)))::date,
    (NOW() - INTERVAL '1 day' * ((c.customer_id * s.n * 13) % 700) + INTERVAL '1 month' * (ARRAY[3,6,9,12,18,24])[1 + ((c.customer_id + s.n) % 6)])::date,
    CASE
        WHEN (c.customer_id * s.n) % 10 < 6 THEN 'CLOSED'
        WHEN (c.customer_id * s.n) % 10 < 8 THEN 'ACTIVE'
        ELSE 'DEFAULTED'
    END
FROM customers c
CROSS JOIN generate_series(1, 3) AS s(n);

-- 3. Repayments for CLOSED loans
INSERT INTO repayments (loan_id, customer_id, payment_date, amount_paid, days_late)
SELECT
    l.loan_id,
    l.customer_id,
    (l.disbursement_date + (gs.m || ' months')::interval + ((l.loan_id * gs.m * 7 % 21) - 12 || ' days')::interval)::date,
    ROUND((l.principal_amount / l.tenure_months) * (0.85 + (l.loan_id * gs.m * 3 % 16) / 100.0), 2),
    GREATEST(0, (l.loan_id * gs.m * 7 % 21) - 12)
FROM loans l
CROSS JOIN generate_series(1, l.tenure_months) AS gs(m)
WHERE l.status = 'CLOSED'
LIMIT 25000;

-- 4. CRB Reports
INSERT INTO crb_reports (customer_id, crb_name, report_date, bureau_score, raw_report, extracted_metrics)
SELECT
    c.customer_id,
    (ARRAY['TransUnion','Metropol','CreditInfo'])[1 + (c.customer_id % 3)],
    (NOW() - INTERVAL '1 day' * (c.customer_id % 90))::date,
    300 + (c.customer_id * 173 % 551),
    jsonb_build_object('source', 'synthetic_seed', 'customer_id', c.customer_id),
    jsonb_build_object(
        'open_accounts', (c.customer_id * 7 % 8) + 1,
        'npa_accounts', CASE WHEN c.customer_id % 8 < 2 THEN 1 ELSE 0 END,
        'inquiry_count_6m', c.customer_id % 6,
        'total_outstanding', c.credit_score * 200
    )
FROM customers c;

-- 5. Score events (initial scoring)
INSERT INTO credit_score_events (
    customer_id, final_score, score_band, llm_provider, llm_model_name, model_target, scored_at
)
SELECT
    c.customer_id,
    c.credit_score,
    CASE
        WHEN c.credit_score >= 750 THEN 'EXCELLENT'
        WHEN c.credit_score >= 670 THEN 'GOOD'
        WHEN c.credit_score >= 580 THEN 'FAIR'
        WHEN c.credit_score >= 500 THEN 'POOR'
        ELSE 'VERY_POOR'
    END,
    'openai', 'gpt-4o-mini',
    CASE WHEN c.customer_id % 10 = 0 THEN 'challenger' ELSE 'champion' END,
    NOW() - INTERVAL '1 day' * (c.customer_id % 180)
FROM customers c;

-- 5b. Re-score events (1/3 of customers scored again more recently)
INSERT INTO credit_score_events (
    customer_id, final_score, score_band, llm_provider, llm_model_name, model_target, scored_at
)
SELECT
    c.customer_id,
    LEAST(850, GREATEST(300, c.credit_score + ((c.customer_id * 7) % 51) - 25)),
    CASE
        WHEN LEAST(850, GREATEST(300, c.credit_score + ((c.customer_id * 7) % 51) - 25)) >= 750 THEN 'EXCELLENT'
        WHEN LEAST(850, GREATEST(300, c.credit_score + ((c.customer_id * 7) % 51) - 25)) >= 670 THEN 'GOOD'
        WHEN LEAST(850, GREATEST(300, c.credit_score + ((c.customer_id * 7) % 51) - 25)) >= 580 THEN 'FAIR'
        WHEN LEAST(850, GREATEST(300, c.credit_score + ((c.customer_id * 7) % 51) - 25)) >= 500 THEN 'POOR'
        ELSE 'VERY_POOR'
    END,
    'openai', 'gpt-4o-mini',
    CASE WHEN c.customer_id % 10 = 0 THEN 'challenger' ELSE 'champion' END,
    NOW() - INTERVAL '1 day' * ((c.customer_id * 3) % 90)
FROM customers c
WHERE c.customer_id % 3 = 0;

-- 6. Disputes (5% of customers)
INSERT INTO disputes (customer_id, description, status, submitted_at)
SELECT
    c.customer_id,
    'Customer disputes credit record accuracy. Reference: DISP-' || c.customer_id,
    (ARRAY['OPEN','OPEN','UNDER_REVIEW','RESOLVED','CLOSED'])[1 + (c.customer_id % 5)],
    NOW() - INTERVAL '1 day' * (c.customer_id % 45)
FROM customers c
WHERE c.customer_id % 20 = 0;

-- Summary
SELECT tbl, cnt FROM (
    SELECT 'customers' AS tbl, COUNT(*) AS cnt FROM customers
    UNION ALL SELECT 'loans', COUNT(*) FROM loans
    UNION ALL SELECT 'repayments', COUNT(*) FROM repayments
    UNION ALL SELECT 'crb_reports', COUNT(*) FROM crb_reports
    UNION ALL SELECT 'score_events', COUNT(*) FROM credit_score_events
    UNION ALL SELECT 'disputes', COUNT(*) FROM disputes
) x ORDER BY tbl;
