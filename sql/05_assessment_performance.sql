-- One row per assessment: participation, scores, lateness, how hard it is
-- relative to the course's other assessments, and how many students stopped
-- submitting since the previous one.

CREATE OR REPLACE TABLE agg_assessment_performance AS
WITH enrolled AS (
    SELECT code_module, code_presentation, COUNT(*) AS enrolled
    FROM fact_enrollment
    GROUP BY ALL
),
per_assessment AS (
    SELECT
        a.code_module,
        a.code_presentation,
        a.id_assessment,
        a.assessment_type,
        a.due_day,
        a.weight,
        COUNT(sa.id_student)                                         AS submissions,
        ROUND(AVG(sa.score), 1)                                      AS avg_score,
        ROUND(MEDIAN(sa.score), 1)                                   AS median_score,
        COUNT(*) FILTER (WHERE sa.score < 40)                        AS below_pass_mark,
        COUNT(*) FILTER (WHERE sa.submitted_day > a.due_day AND NOT sa.is_banked) AS late,
        COUNT(*) FILTER (WHERE NOT sa.is_banked)                     AS not_banked
    FROM stg_assessments a
    LEFT JOIN stg_student_assessment sa USING (id_assessment)
    GROUP BY ALL
)
SELECT
    p.code_module,
    p.code_presentation,
    p.code_module || '-' || p.code_presentation AS course_run,
    p.id_assessment,
    p.assessment_type,
    ROW_NUMBER() OVER (PARTITION BY p.code_module, p.code_presentation ORDER BY p.due_day NULLS LAST, p.id_assessment)
        AS assessment_order,
    p.due_day,
    p.weight,
    e.enrolled,
    p.submissions,
    ROUND(p.submissions / e.enrolled, 4)                        AS submission_rate,
    p.avg_score,
    p.median_score,
    ROUND(p.below_pass_mark / NULLIF(p.submissions, 0), 4)      AS share_below_pass_mark,
    ROUND(p.late / NULLIF(p.not_banked, 0), 4)                  AS late_rate,
    -- 1 = lowest average score in the course run
    RANK() OVER (PARTITION BY p.code_module, p.code_presentation ORDER BY p.avg_score) AS difficulty_rank,
    p.submissions - LAG(p.submissions) OVER (
        PARTITION BY p.code_module, p.code_presentation
        ORDER BY p.due_day NULLS LAST, p.id_assessment
    )                                                           AS change_in_submissions
FROM per_assessment p
JOIN enrolled e USING (code_module, code_presentation)
ORDER BY p.code_module, p.code_presentation, assessment_order;
