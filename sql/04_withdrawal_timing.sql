-- When do students withdraw? Weekly and running withdrawal rate per course run.
-- Uses only withdrawn students who have an unregistration date.

CREATE OR REPLACE TABLE agg_withdrawal_timing AS
WITH runs AS (
    SELECT code_module, code_presentation, course_run, course_length_days, COUNT(*) AS enrolled
    FROM fact_enrollment
    GROUP BY ALL
),
weeks AS (
    SELECT r.*, w.week
    FROM runs r
    CROSS JOIN range(-10, 40) AS w(week)
    WHERE w.week * 7 < r.course_length_days
),
withdrawals AS (
    SELECT
        code_module,
        code_presentation,
        FLOOR(unregistration_day / 7)::INTEGER AS week,
        COUNT(*) AS withdrawals
    FROM fact_enrollment
    WHERE is_withdrawn = 1 AND unregistration_day IS NOT NULL
    GROUP BY ALL
)
SELECT
    w.code_module,
    w.code_presentation,
    w.course_run,
    w.week,
    w.enrolled,
    COALESCE(wd.withdrawals, 0) AS withdrawals,
    SUM(COALESCE(wd.withdrawals, 0)) OVER run_to_date AS cumulative_withdrawals,
    ROUND(COALESCE(wd.withdrawals, 0) / w.enrolled, 4) AS weekly_withdrawal_rate,
    ROUND(SUM(COALESCE(wd.withdrawals, 0)) OVER run_to_date / w.enrolled, 4) AS cumulative_withdrawal_rate
FROM weeks w
LEFT JOIN withdrawals wd USING (code_module, code_presentation, week)
WINDOW run_to_date AS (
    PARTITION BY w.code_module, w.code_presentation
    ORDER BY w.week
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
ORDER BY ALL;
