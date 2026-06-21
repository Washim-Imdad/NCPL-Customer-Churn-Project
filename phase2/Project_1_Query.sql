SET GLOBAL local_infile = 1;
CREATE TABLE customers (
    CustomerID              VARCHAR(20)   NOT NULL PRIMARY KEY,
    Country                 VARCHAR(50),
    State                   VARCHAR(50),
    City                    VARCHAR(100),
    `Zip Code`              INT,
    Latitude                DECIMAL(10, 6),
    Longitude               DECIMAL(10, 6),
    Gender                  VARCHAR(10),
    `Senior Citizen`        VARCHAR(5),
    Partner                 VARCHAR(5),
    Dependents              VARCHAR(5),
    `Tenure Months`         INT,
    `Phone Service`         VARCHAR(20),
    `Multiple Lines`        VARCHAR(25),
    `Internet Service`      VARCHAR(20),
    `Online Security`       VARCHAR(25),
    `Online Backup`         VARCHAR(25),
    `Device Protection`     VARCHAR(25),
    `Tech Support`          VARCHAR(25),
    `Streaming TV`          VARCHAR(25),
    `Streaming Movies`      VARCHAR(25),
    Contract                VARCHAR(20),
    `Paperless Billing`     VARCHAR(5),
    `Payment Method`        VARCHAR(40),
    `Monthly Charges`       DECIMAL(10, 2),
    `Total Charges`         DECIMAL(10, 2),
    `Churn Label`           VARCHAR(5),
    `Churn Value`           TINYINT,
    `Churn Score`           INT,
    CLTV                    INT,
    `Churn Reason`          VARCHAR(100),
    Gender_encoded          TINYINT,
    `Senior Citizen_encoded` TINYINT,
    Partner_encoded         TINYINT,
    Dependents_encoded      TINYINT,
    `Phone Service_encoded` TINYINT,
    `Paperless Billing_encoded` TINYINT,
    `Multiple Lines_encoded` TINYINT,
    `Online Security_encoded` TINYINT,
    `Online Backup_encoded` TINYINT,
    `Device Protection_encoded` TINYINT,
    `Tech Support_encoded`  TINYINT,
    `Streaming TV_encoded`  TINYINT,
    `Streaming Movies_encoded` TINYINT,
    Contract_encoded        TINYINT,
    `Internet Service_encoded` TINYINT,
    `Payment Method_encoded` TINYINT,
    Churn_encoded           TINYINT,
    `Tenure Group`          VARCHAR(20),
    `Avg Monthly Usage`     DECIMAL(10, 4),
    `Service Count`         TINYINT,
    `Payment Risk`          VARCHAR(10),
    `Risk Segment`          VARCHAR(15)
);
LOAD DATA LOCAL INFILE 'C:/Users/Washim/Desktop/Project 1 NCPL/output/phase1/cleaned_telco_churn.csv'
INTO TABLE customers
FIELDS TERMINATED BY ',' 
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS;
SELECT * FROM customers;
SELECT COUNT(*) FROM customers;

-- =============================================================================
-- QUERY 1: Overall Churn Rate & Customer Count
-- REASON:
--   Purpose: Establish the baseline KPI for executive reporting.
--   Business Question: What percentage of our customer base has churned?
--   Action: Track this metric monthly; set a retention target below 26.5%.
-- =============================================================================
SELECT
    COUNT(*)                                              AS total_customers,
    SUM(Churn_encoded)                                    AS churned_customers,
    SUM(CASE WHEN Churn_encoded = 0 THEN 1 ELSE 0 END)    AS retained_customers,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)       AS churn_rate_pct
FROM customers;


-- =============================================================================
-- QUERY 2: Total Revenue — Retained vs Churned
-- REASON:
--   Purpose: Quantify historical revenue associated with churned customers.
--   Business Question: How much total billing revenue did we lose to churn?
--   Action: Use this to justify retention program budget and ROI targets.
-- =============================================================================
SELECT
    CASE Churn_encoded WHEN 1 THEN 'Churned' ELSE 'Retained' END AS customer_status,
    COUNT(*)                        AS customer_count,
    ROUND(SUM(`Total Charges`), 2)  AS total_revenue,
    ROUND(AVG(`Total Charges`), 2)  AS avg_total_charges
FROM customers
GROUP BY Churn_encoded
ORDER BY Churn_encoded DESC;


-- =============================================================================
-- QUERY 3: Average Revenue Per User (ARPU)
-- REASON:
--   Purpose: Compute the standard telecom profitability metric.
--   Business Question: What is our average monthly revenue per customer?
--   Action: Benchmark ARPU against industry; monitor trend after retention campaigns.
-- =============================================================================
SELECT
    ROUND(AVG(`Monthly Charges`), 2) AS arpu_overall,
    ROUND(MIN(`Monthly Charges`), 2) AS min_monthly_charge,
    ROUND(MAX(`Monthly Charges`), 2) AS max_monthly_charge,
    ROUND(STDDEV(`Monthly Charges`), 2) AS stddev_monthly_charge
FROM customers;


-- =============================================================================
-- QUERY 4: Average CLTV by Churn Status
-- REASON:
--   Purpose: Compare customer lifetime value between retained and churned groups.
--   Business Question: Are we losing high-value or low-value customers?
--   Action: If churned CLTV is high, prioritize proactive outreach to similar profiles.
-- =============================================================================
SELECT
    `Churn Label`                   AS churn_status,
    COUNT(*)                        AS customer_count,
    ROUND(AVG(CLTV), 2)             AS avg_cltv,
    ROUND(MIN(CLTV), 2)             AS min_cltv,
    ROUND(MAX(CLTV), 2)             AS max_cltv
FROM customers
GROUP BY `Churn Label`
ORDER BY `Churn Label`;

-- =============================================================================
-- QUERY 5: Churn Rate by Payment Method
-- REASON:
--   Purpose: Assess whether payment friction drives attrition.
--   Business Question: Do electronic check payers churn more than auto-pay customers?
--   Action: Migrate electronic check users to automatic bank/card payment with incentives.
-- =============================================================================
SELECT
    `Payment Method`,
    COUNT(*)                                            AS customer_count,
    SUM(Churn_encoded)                                  AS churned_count,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM customers
GROUP BY `Payment Method`
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- QUERY 6: Churn Rate by Senior Citizen Status
-- REASON:
--   Purpose: Support age-targeted retention and product design decisions.
--   Business Question: Do senior citizens churn at a different rate than others?
--   Action: Tailor support channels and pricing packages for senior segments if needed.
-- =============================================================================
SELECT
    `Senior Citizen`,
    COUNT(*)                                            AS customer_count,
    SUM(Churn_encoded)                                  AS churned_count,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM customers
GROUP BY `Senior Citizen`
ORDER BY `Senior Citizen`;


-- =============================================================================
-- QUERY 7: Churn Rate by Partner and Dependents (Family Profile)
-- REASON:
--   Purpose: Test whether family/household customers show higher loyalty.
--   Business Question: Should we promote family bundle packages to reduce churn?
--   Action: Design bundled offers for solo customers (No partner, No dependents).
-- =============================================================================
SELECT
    Partner,
    Dependents,
    COUNT(*)                                            AS customer_count,
    SUM(Churn_encoded)                                  AS churned_count,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM customers
GROUP BY Partner, Dependents
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- QUERY 8: Top 10 Cities by Churn Rate (Minimum 30 Customers)
-- REASON:
--   Purpose: Enable geo-targeted marketing and regional retention campaigns.
--   Business Question: Which cities have the worst churn relative to customer volume?
--   Action: Deploy regional competitive analysis and localized offers in top churn cities.
-- =============================================================================
SELECT
    City,
    State,
    COUNT(*)                                            AS customer_count,
    SUM(Churn_encoded)                                  AS churned_count,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM customers
GROUP BY City, State
HAVING COUNT(*) >= 30
ORDER BY churn_rate_pct DESC
LIMIT 10;


-- =============================================================================
-- QUERY 9: ARPU by Contract Type
-- REASON:
--   Purpose: Link contract commitment to revenue quality.
--   Business Question: Do month-to-month customers pay less as well as churn more?
--   Action: Balance upgrade incentives against revenue impact when converting contracts.
-- =============================================================================
SELECT
    Contract,
    COUNT(*)                        AS customer_count,
    ROUND(AVG(`Monthly Charges`), 2) AS arpu,
    ROUND(SUM(`Monthly Charges`), 2) AS total_monthly_revenue,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM customers
GROUP BY Contract
ORDER BY arpu DESC;


-- =============================================================================
-- QUERY 10: ARPU by Internet Service Tier
-- REASON:
--   Purpose: Understand revenue mix across product tiers.
--   Business Question: Is fiber generating enough premium revenue to offset its churn rate?
--   Action: Evaluate fiber pricing strategy vs. competitive fiber offers in market.
-- =============================================================================
SELECT
    `Internet Service`,
    COUNT(*)                        AS customer_count,
    ROUND(AVG(`Monthly Charges`), 2) AS arpu,
    ROUND(SUM(`Monthly Charges`), 2) AS total_monthly_revenue,
    ROUND(AVG(`Total Charges`), 2) AS avg_total_charges,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM customers
GROUP BY `Internet Service`
ORDER BY arpu DESC;


-- =============================================================================
-- QUERY 11: Revenue at Risk — High-Risk Non-Churned Customers
-- REASON:
--   Purpose: Estimate monthly revenue exposure from the high-risk retained segment.
--   Business Question: If all high-risk retained customers churn, what monthly revenue is lost?
--   Action: Allocate retention budget proportional to this revenue-at-risk figure.
-- =============================================================================
SELECT
    `Payment Risk`,
    COUNT(*)                                            AS retained_customers,
    ROUND(SUM(`Monthly Charges`), 2)                    AS monthly_revenue_at_risk,
    ROUND(AVG(`Monthly Charges`), 2)                    AS avg_monthly_charge,
    ROUND(AVG(`Churn Score`), 1)                          AS avg_churn_score
FROM customers
WHERE Churn_encoded = 0
GROUP BY `Payment Risk`
ORDER BY FIELD(`Payment Risk`, 'High', 'Medium', 'Low');


-- =============================================================================
-- QUERY 12: High-Value Customer Churn Rate (CLTV > 75th Percentile)
-- REASON:
--   Purpose: Protect the most profitable customer accounts.
--   Business Question: Are our highest-CLTV customers leaving at an alarming rate?
--   Action: Assign dedicated account managers to high-CLTV customers above the threshold.
-- =============================================================================
WITH ordered AS (
    SELECT
        CLTV,
        Churn_encoded,
        ROW_NUMBER() OVER (ORDER BY CLTV) AS rn,
        COUNT(*) OVER () AS total
    FROM customers
),
cltv_threshold AS (
    SELECT CLTV AS p75_cltv
    FROM ordered
    WHERE rn = CEIL(total * 0.75)
    LIMIT 1
)
SELECT
    CASE
        WHEN c.CLTV >= t.p75_cltv THEN 'High Value (Top 25%)'
        ELSE 'Standard Value'
    END                                                 AS value_segment,
    COUNT(*)                                            AS customer_count,
    SUM(c.Churn_encoded)                                AS churned_count,
    ROUND(SUM(c.Churn_encoded) * 100.0 / COUNT(*), 2)   AS churn_rate_pct,
    ROUND(AVG(c.CLTV), 2)                               AS avg_cltv
FROM customers c
CROSS JOIN cltv_threshold t
GROUP BY value_segment, t.p75_cltv
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- QUERY 13: Total Lost CLTV from Churned Customers
-- REASON:
--   Purpose: Quantify total lifetime value destroyed by customer attrition.
--   Business Question: What is the full CLTV impact of customers who already left?
--   Action: Use this figure in executive business cases for retention investment.
-- =============================================================================
SELECT
    COUNT(*)                        AS churned_customers,
    ROUND(SUM(CLTV), 2)             AS total_lost_cltv,
    ROUND(AVG(CLTV), 2)             AS avg_lost_cltv_per_customer,
    ROUND(SUM(`Monthly Charges`), 2) AS total_lost_monthly_revenue
FROM customers
WHERE Churn_encoded = 1;


-- =============================================================================
-- QUERY 14: Top 10 Stated Churn Reasons
-- REASON:
--   Purpose: Identify dominant competitive and service drivers of attrition.
--   Business Question: Why are customers leaving, in their own words?
--   Action: Address top 3 reasons in product, pricing, and competitive response plans.
-- =============================================================================
SELECT
    `Churn Reason`,
    COUNT(*)                                            AS customer_count,
    ROUND(COUNT(*) * 100.0 / (
        SELECT COUNT(*) FROM customers WHERE Churn_encoded = 1
    ), 2)                                               AS pct_of_churned
FROM customers
WHERE Churn_encoded = 1
  AND `Churn Reason` != 'Not Applicable'
GROUP BY `Churn Reason`
ORDER BY customer_count DESC
LIMIT 10;


-- =============================================================================
-- QUERY 15: Churn Reasons Ranked by Average Monthly Charges
-- REASON:
--   Purpose: Prioritize churn reasons that affect high-paying customers.
--   Business Question: Which churn drivers are most costly in terms of monthly revenue?
--   Action: Focus premium retention efforts on high-ARPU churn reason categories.
-- =============================================================================
SELECT
    `Churn Reason`,
    COUNT(*)                        AS customer_count,
    ROUND(AVG(`Monthly Charges`), 2) AS avg_monthly_charge,
    ROUND(AVG(CLTV), 2)             AS avg_cltv
FROM customers
WHERE Churn_encoded = 1
  AND `Churn Reason` != 'Not Applicable'
GROUP BY `Churn Reason`
HAVING COUNT(*) >= 10
ORDER BY avg_monthly_charge DESC
LIMIT 10;


-- =============================================================================
-- QUERY 16: Churn Rate by Service Count (Add-on Engagement)
-- REASON:
--   Purpose: Test whether deeper product engagement reduces attrition.
--   Business Question: Do customers with more add-on services churn less?
--   Action: Promote add-on bundles (security, streaming, support) during onboarding.
-- =============================================================================
SELECT
    `Service Count`,
    COUNT(*)                                            AS customer_count,
    SUM(Churn_encoded)                                  AS churned_count,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM customers
GROUP BY `Service Count`
ORDER BY `Service Count`;


-- =============================================================================
-- QUERY 17: Fiber Customers — Tech Support Impact on Churn
-- REASON:
--   Purpose: Assess whether tech support upsell reduces fiber customer churn.
--   Business Question: Do fiber customers without tech support churn more?
--   Action: Offer discounted tech support bundles to fiber subscribers without it.
-- =============================================================================
SELECT
    `Tech Support`,
    COUNT(*)                                            AS customer_count,
    SUM(Churn_encoded)                                  AS churned_count,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM customers
WHERE `Internet Service` = 'Fiber optic'
GROUP BY `Tech Support`
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- QUERY 18: High-Risk Rule Validation (Month-to-Month + Electronic Check + Paperless)
-- REASON:
--   Purpose: Independently validate the engineered high-risk customer rule in SQL.
--   Business Question: Does this specific combination truly correlate with high churn?
--   Action: Confirm rule for CRM automation and trigger retention workflows on match.
-- =============================================================================
SELECT
    CASE
        WHEN Contract = 'Month-to-month'
         AND `Payment Method` = 'Electronic check'
         AND `Paperless Billing` = 'Yes' THEN 'High Risk Rule Match'
        ELSE 'No Match'
    END                                                 AS rule_match,
    COUNT(*)                                            AS customer_count,
    SUM(Churn_encoded)                                  AS churned_count,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM customers
GROUP BY rule_match
ORDER BY churn_rate_pct DESC;


-- =============================================================================
-- QUERY 19: Churn Rate by Tenure Month (Monthly Churn Proxy)
-- REASON:
--   Purpose: Proxy for "monthly churn rate" since no calendar date exists in dataset.
--   Business Question: At which tenure month does churn peak after signup?
--   Action: Time retention touchpoints (calls, offers) to peak-risk tenure months.
-- =============================================================================
SELECT
    `Tenure Months`,
    COUNT(*)                                            AS customer_count,
    SUM(Churn_encoded)                                  AS churned_count,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM customers
GROUP BY `Tenure Months`
HAVING COUNT(*) >= 20
ORDER BY churn_rate_pct DESC
LIMIT 15;


-- =============================================================================
-- QUERY 20: Top 20 At-Risk Active Customers (RANK by Churn Score)
-- REASON:
--   Purpose: Generate an actionable call list for the retention team.
--   Business Question: Which retained customers should we contact immediately?
--   Action: Export this list to CRM; assign agents to call within 48 hours.
-- =============================================================================
SELECT
    CustomerID,
    `Churn Score`,
    `Monthly Charges`,
    CLTV,
    Contract,
    `Internet Service`,
    `Payment Method`,
    `Tenure Months`,
    `Payment Risk`,
    `Risk Segment`,
    RANK() OVER (ORDER BY `Churn Score` DESC)           AS risk_rank
FROM customers
WHERE Churn_encoded = 0
ORDER BY `Churn Score` DESC
LIMIT 20;


-- =============================================================================
-- QUERY 21: Churn Rate by Monthly Charge Quartile (NTILE)
-- REASON:
--   Purpose: Determine whether premium pricing correlates with higher attrition.
--   Business Question: Do customers in the highest price quartile churn more?
--   Action: Review pricing for top-quartile plans; consider loyalty discounts.
-- =============================================================================
WITH charge_quartiles AS (
    SELECT
        CustomerID,
        Churn_encoded,
        `Monthly Charges`,
        NTILE(4) OVER (ORDER BY `Monthly Charges`) AS charge_quartile
    FROM customers
)
SELECT
    charge_quartile,
    COUNT(*)                                            AS customer_count,
    ROUND(MIN(`Monthly Charges`), 2)                    AS min_charge,
    ROUND(MAX(`Monthly Charges`), 2)                    AS max_charge,
    SUM(Churn_encoded)                                  AS churned_count,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct
FROM charge_quartiles
GROUP BY charge_quartile
ORDER BY charge_quartile;


-- =============================================================================
-- QUERY 22: Running Total of Lost CLTV (Cumulative Pareto)
-- REASON:
--   Purpose: Show cumulative CLTV loss concentration among churned customers.
--   Business Question: What fraction of total CLTV loss comes from the top churned accounts?
--   Action: Prioritize win-back campaigns on high-CLTV churned customers first.
-- =============================================================================
WITH churned_ranked AS (
    SELECT
        CustomerID,
        CLTV,
        `Monthly Charges`,
        `Churn Reason`,
        SUM(CLTV) OVER (ORDER BY CLTV DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_lost_cltv,
        SUM(CLTV) OVER () AS total_lost_cltv
    FROM customers
    WHERE Churn_encoded = 1
)
SELECT
    CustomerID,
    CLTV,
    `Monthly Charges`,
    `Churn Reason`,
    running_lost_cltv,
    ROUND(running_lost_cltv * 100.0 / total_lost_cltv, 2) AS cumulative_pct_of_loss
FROM churned_ranked
ORDER BY CLTV DESC
LIMIT 20;

-- =============================================================================
-- QUERY 23: Cross-Segment Churn — Contract Type within Internet Service
-- REASON:
--   Purpose: Provide a cross-tab view for targeted segment-specific strategies.
--   Business Question: Which contract+internet combinations are most dangerous?
--   Action: Design fiber month-to-month specific offers; promote DSL two-year upgrades.
-- =============================================================================
SELECT
    `Internet Service`,
    Contract,
    COUNT(*)                                            AS customer_count,
    SUM(Churn_encoded)                                  AS churned_count,
    ROUND(SUM(Churn_encoded) * 100.0 / COUNT(*), 2)     AS churn_rate_pct,
    ROUND(AVG(`Monthly Charges`), 2)                    AS avg_monthly_charge
FROM customers
GROUP BY `Internet Service`, Contract
ORDER BY churn_rate_pct DESC;