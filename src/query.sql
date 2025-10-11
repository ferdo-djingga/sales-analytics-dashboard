-- --------------------------------------------
-- Sales & Transaction Analytics — Sample SQL
-- Works on ANSI SQL (tested with SQLite/Postgres)
-- --------------------------------------------

-- SCHEMA (reference; the Python pipeline reads CSVs instead)
-- CREATE TABLE customers (
--   customer_id   TEXT PRIMARY KEY,
--   signup_date   DATE,
--   segment       TEXT,        -- e.g., Retail / Enterprise / SMB
--   channel       TEXT         -- e.g., Online / Partner / Direct
-- );
--
-- CREATE TABLE transactions (
--   txn_id        TEXT PRIMARY KEY,
--   txn_date      DATE,
--   customer_id   TEXT REFERENCES customers(customer_id),
--   product       TEXT,
--   quantity      INTEGER,
--   unit_price    NUMERIC(10,2),
--   currency      TEXT
-- );

-- 1) Core facts
-- Total revenue & order count
SELECT
  SUM(quantity * unit_price)        AS total_revenue,
  COUNT(DISTINCT txn_id)            AS orders
FROM transactions;

-- 2) Daily revenue trend
SELECT
  txn_date,
  SUM(quantity * unit_price) AS revenue
FROM transactions
GROUP BY txn_date
ORDER BY txn_date;

-- 3) Monthly revenue and orders
SELECT
  DATE_TRUNC('month', txn_date) AS month,
  SUM(quantity * unit_price)    AS revenue,
  COUNT(DISTINCT txn_id)        AS orders
FROM transactions
GROUP BY DATE_TRUNC('month', txn_date)
ORDER BY month;

-- 4) Average Order Value (AOV) by month
WITH order_revenue AS (
  SELECT
    txn_id,
    SUM(quantity * unit_price) AS order_amount
  FROM transactions
  GROUP BY txn_id
)
SELECT
  DATE_TRUNC('month', t.txn_date) AS month,
  SUM(o.order_amount) / COUNT(*)  AS aov
FROM transactions t
JOIN order_revenue o ON t.txn_id = o.txn_id
GROUP BY DATE_TRUNC('month', t.txn_date)
ORDER BY month;

-- 5) Top products by revenue
SELECT
  product,
  SUM(quantity)                   AS units_sold,
  SUM(quantity * unit_price)      AS revenue
FROM transactions
GROUP BY product
ORDER BY revenue DESC
LIMIT 10;

-- 6) Revenue by customer segment & channel
SELECT
  c.segment,
  c.channel,
  SUM(t.quantity * t.unit_price)  AS revenue,
  COUNT(DISTINCT t.txn_id)        AS orders
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
GROUP BY c.segment, c.channel
ORDER BY revenue DESC;

-- 7) New vs Returning customers (monthly)
WITH first_purchase AS (
  SELECT customer_id, MIN(txn_date) AS first_txn_date
  FROM transactions
  GROUP BY customer_id
),
tx AS (
  SELECT
    t.txn_id,
    t.customer_id,
    t.txn_date,
    CASE
      WHEN DATE_TRUNC('month', t.txn_date) = DATE_TRUNC('month', f.first_txn_date)
        THEN 'New'
      ELSE 'Returning'
    END AS customer_type,
    (t.quantity * t.unit_price) AS amount
  FROM transactions t
  JOIN first_purchase f USING (customer_id)
)
SELECT
  DATE_TRUNC('month', txn_date) AS month,
  customer_type,
  SUM(amount)                   AS revenue,
  COUNT(DISTINCT txn_id)        AS orders
FROM tx
GROUP BY DATE_TRUNC('month', txn_date), customer_type
ORDER BY month, customer_type;

-- 8) Simple cohort (by signup month) revenue contribution
SELECT
  DATE_TRUNC('month', c.signup_date)      AS cohort_month,
  DATE_TRUNC('month', t.txn_date)         AS revenue_month,
  SUM(t.quantity * t.unit_price)          AS revenue
FROM customers c
JOIN transactions t ON t.customer_id = c.customer_id
GROUP BY DATE_TRUNC('month', c.signup_date), DATE_TRUNC('month', t.txn_date)
ORDER BY cohort_month, revenue_month;