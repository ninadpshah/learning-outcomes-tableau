-- Average weekly clicks per student, split by final result.
-- A date spine makes sure every week appears even if nobody clicked,
-- so lines in Tableau do not skip weeks.

CREATE OR REPLACE TABLE agg_weekly_engagement AS
WITH weeks AS (
    SELECT c.code_module, c.code_presentation, w.week
    FROM stg_courses c
    CROSS JOIN range(-2, 40) AS w(week)          -- two weeks before start through week 39
    WHERE w.week * 7 < c.course_length_days
),
cohorts AS (
    SELECT code_module, code_presentation, final_result, COUNT(*) AS students
    FROM fact_enrollment
    GROUP BY ALL
),
weekly_clicks AS (
    SELECT
        v.code_module,
        v.code_presentation,
        f.final_result,
        FLOOR(v.date / 7)::INTEGER                AS week,
        SUM(v.sum_click)                          AS clicks,
        COUNT(DISTINCT v.id_student)              AS active_students
    FROM stg_student_vle v
    JOIN fact_enrollment f USING (code_module, code_presentation, id_student)
    GROUP BY ALL
)
SELECT
    w.code_module,
    w.code_presentation,
    w.code_module || '-' || w.code_presentation   AS course_run,
    w.week,
    co.final_result,
    co.students,
    COALESCE(wc.clicks, 0)                        AS clicks,
    COALESCE(wc.active_students, 0)               AS active_students,
    ROUND(COALESCE(wc.clicks, 0) / co.students, 2)          AS clicks_per_student,
    ROUND(COALESCE(wc.active_students, 0) / co.students, 4) AS share_active
FROM weeks w
JOIN cohorts co USING (code_module, code_presentation)
LEFT JOIN weekly_clicks wc
    USING (code_module, code_presentation, final_result, week)
ORDER BY ALL;
