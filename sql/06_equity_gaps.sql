-- Pass and withdrawal rates by student group, compared with everyone in the
-- same course run. Groups under 10 students are suppressed.

CREATE OR REPLACE TABLE agg_equity_gaps AS
WITH long AS (
    SELECT code_module, code_presentation, course_run, 'Deprivation (IMD band)' AS dimension, imd_band AS grp, is_pass, is_withdrawn FROM fact_enrollment
    UNION ALL
    SELECT code_module, code_presentation, course_run, 'Age band', age_band, is_pass, is_withdrawn FROM fact_enrollment
    UNION ALL
    SELECT code_module, code_presentation, course_run, 'Prior education', highest_education, is_pass, is_withdrawn FROM fact_enrollment
    UNION ALL
    SELECT code_module, code_presentation, course_run, 'Disability', disability, is_pass, is_withdrawn FROM fact_enrollment
    UNION ALL
    SELECT code_module, code_presentation, course_run, 'Gender', gender, is_pass, is_withdrawn FROM fact_enrollment
    UNION ALL
    SELECT code_module, code_presentation, course_run, 'First attempt',
           CASE WHEN is_first_attempt THEN 'First attempt' ELSE 'Repeat' END, is_pass, is_withdrawn
    FROM fact_enrollment
),
baseline AS (
    SELECT code_module, code_presentation, AVG(is_pass) AS run_pass_rate, AVG(is_withdrawn) AS run_withdrawal_rate
    FROM fact_enrollment
    GROUP BY ALL
),
groups AS (
    SELECT code_module, code_presentation, course_run, dimension, grp,
           COUNT(*) AS students, AVG(is_pass) AS pass_rate, AVG(is_withdrawn) AS withdrawal_rate
    FROM long
    GROUP BY ALL
)
SELECT
    g.code_module,
    g.code_presentation,
    g.course_run,
    g.dimension,
    g.grp AS student_group,
    g.students,
    g.students < 10                                                       AS is_suppressed,
    CASE WHEN g.students >= 10 THEN ROUND(g.pass_rate, 4) END             AS pass_rate,
    CASE WHEN g.students >= 10 THEN ROUND(g.withdrawal_rate, 4) END       AS withdrawal_rate,
    ROUND(b.run_pass_rate, 4)                                             AS run_pass_rate,
    ROUND(b.run_withdrawal_rate, 4)                                       AS run_withdrawal_rate,
    CASE WHEN g.students >= 10 THEN ROUND((g.pass_rate - b.run_pass_rate) * 100, 1) END             AS pass_gap_pp,
    CASE WHEN g.students >= 10 THEN ROUND((g.withdrawal_rate - b.run_withdrawal_rate) * 100, 1) END AS withdrawal_gap_pp
FROM groups g
JOIN baseline b USING (code_module, code_presentation)
ORDER BY ALL;
