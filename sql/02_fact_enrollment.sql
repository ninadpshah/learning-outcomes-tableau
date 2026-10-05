-- One row per student per course run: outcome, demographics, early
-- engagement and coursework measures. This is the main Tableau table.

CREATE OR REPLACE TABLE fact_enrollment AS
WITH clicks AS (
    SELECT
        code_module,
        code_presentation,
        id_student,
        SUM(sum_click)                                        AS total_clicks,
        SUM(sum_click) FILTER (WHERE date BETWEEN 0 AND 27)   AS early_clicks,
        SUM(sum_click) FILTER (WHERE date < 0)                AS pre_start_clicks,
        COUNT(DISTINCT date)                                  AS active_days,
        MIN(date)                                             AS first_active_day,
        MAX(date)                                             AS last_active_day
    FROM stg_student_vle
    GROUP BY ALL
),
-- First scheduled coursework (not the exam) in each course run.
first_assessment AS (
    SELECT code_module, code_presentation, id_assessment, due_day
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY code_module, code_presentation
                ORDER BY due_day, id_assessment
            ) AS rn
        FROM stg_assessments
        WHERE assessment_type <> 'Exam' AND due_day IS NOT NULL
    )
    WHERE rn = 1
),
coursework AS (
    SELECT
        a.code_module,
        a.code_presentation,
        sa.id_student,
        COUNT(*)                                                         AS assessments_submitted,
        AVG(sa.score)                                                    AS avg_score,
        SUM(sa.score * a.weight) / NULLIF(SUM(a.weight) FILTER (WHERE sa.score IS NOT NULL), 0)
                                                                         AS weighted_score,
        COUNT(*) FILTER (WHERE sa.submitted_day > a.due_day AND NOT sa.is_banked) AS late_submissions
    FROM stg_student_assessment sa
    JOIN stg_assessments a USING (id_assessment)
    WHERE a.assessment_type <> 'Exam'
    GROUP BY ALL
),
base AS (
    SELECT
        si.code_module,
        si.code_presentation,
        si.code_module || '-' || si.code_presentation               AS course_run,
        c.start_year,
        c.start_month,
        c.course_length_days,
        si.id_student,
        si.gender,
        si.region,
        si.highest_education,
        si.imd_band,
        si.age_band,
        si.disability,
        si.num_of_prev_attempts,
        si.num_of_prev_attempts = 0                                 AS is_first_attempt,
        si.studied_credits,
        si.final_result,
        CASE WHEN si.final_result IN ('Pass', 'Distinction') THEN 1 ELSE 0 END AS is_pass,
        CASE WHEN si.final_result = 'Withdrawn' THEN 1 ELSE 0 END             AS is_withdrawn,
        CASE WHEN si.final_result = 'Distinction' THEN 1 ELSE 0 END           AS is_distinction,
        CASE WHEN si.final_result = 'Fail' THEN 1 ELSE 0 END                  AS is_fail,
        r.registration_day,
        r.unregistration_day,
        COALESCE(r.unregistration_day < 0, FALSE)                   AS withdrew_before_start,
        COALESCE(cl.total_clicks, 0)                                AS total_clicks,
        COALESCE(cl.early_clicks, 0)                                AS early_clicks,
        COALESCE(cl.pre_start_clicks, 0)                            AS pre_start_clicks,
        COALESCE(cl.active_days, 0)                                 AS active_days,
        cl.first_active_day,
        cl.last_active_day,
        sa1.id_student IS NOT NULL                                  AS submitted_first_assessment,
        COALESCE(cw.assessments_submitted, 0)                       AS assessments_submitted,
        ROUND(cw.avg_score, 1)                                      AS avg_score,
        ROUND(cw.weighted_score, 1)                                 AS weighted_score,
        COALESCE(cw.late_submissions, 0)                            AS late_submissions
    FROM stg_student_info si
    JOIN stg_courses c USING (code_module, code_presentation)
    LEFT JOIN stg_student_registration r USING (code_module, code_presentation, id_student)
    LEFT JOIN clicks cl USING (code_module, code_presentation, id_student)
    LEFT JOIN coursework cw USING (code_module, code_presentation, id_student)
    LEFT JOIN first_assessment fa USING (code_module, code_presentation)
    LEFT JOIN stg_student_assessment sa1
        ON sa1.id_assessment = fa.id_assessment AND sa1.id_student = si.id_student
)
SELECT
    *,
    -- Rank each student against classmates in the same course run (1 = least engaged).
    NTILE(4) OVER (PARTITION BY code_module, code_presentation ORDER BY early_clicks) AS early_engagement_quartile
FROM base;
