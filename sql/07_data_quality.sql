-- Checks run on every build. severity 'error' stops the pipeline;
-- 'warning' is reported and explained in the README.

CREATE OR REPLACE TABLE data_quality_checks AS
SELECT 'Duplicate student-course enrollments' AS check_name, 'error' AS severity,
       (SELECT COUNT(*) FROM (
            SELECT code_module, code_presentation, id_student FROM stg_student_info
            GROUP BY ALL HAVING COUNT(*) > 1)) AS failing_rows,
       'Each student should appear once per course run' AS description
UNION ALL
SELECT 'Enrollments with no matching course', 'error',
       (SELECT COUNT(*) FROM stg_student_info si ANTI JOIN stg_courses c USING (code_module, code_presentation)),
       'Every enrollment must belong to a known course run'
UNION ALL
SELECT 'Assessment results for unknown assessments', 'error',
       (SELECT COUNT(*) FROM stg_student_assessment sa ANTI JOIN stg_assessments a USING (id_assessment)),
       'Every result must link to an assessment'
UNION ALL
SELECT 'Clicks from students not enrolled in the course', 'error',
       (SELECT COUNT(*) FROM stg_student_vle v
            ANTI JOIN stg_student_info si USING (code_module, code_presentation, id_student)),
       'Activity must belong to an enrolled student'
UNION ALL
SELECT 'Scores outside 0-100', 'error',
       (SELECT COUNT(*) FROM stg_student_assessment WHERE score < 0 OR score > 100),
       'Scores are percentages'
UNION ALL
SELECT 'Missing assessment scores', 'warning',
       (SELECT COUNT(*) FROM stg_student_assessment WHERE score IS NULL),
       'Kept in submission counts, left out of averages'
UNION ALL
SELECT 'Withdrawn with no withdrawal date', 'warning',
       (SELECT COUNT(*) FROM fact_enrollment WHERE is_withdrawn = 1 AND unregistration_day IS NULL),
       'Counted in rates, left out of timing charts'
UNION ALL
SELECT 'Withdrawal date but result is not Withdrawn', 'warning',
       (SELECT COUNT(*) FROM fact_enrollment WHERE is_withdrawn = 0 AND unregistration_day IS NOT NULL),
       'Final result is treated as the source of truth'
UNION ALL
SELECT 'Withdrew before the course started', 'warning',
       (SELECT COUNT(*) FROM fact_enrollment WHERE withdrew_before_start),
       'Flagged so they can be excluded when judging course design'
UNION ALL
SELECT 'Unknown deprivation band', 'warning',
       (SELECT COUNT(*) FROM stg_student_info WHERE imd_band = 'Unknown'),
       'Shown as its own group in equity views'
UNION ALL
SELECT 'Assessments with no due date', 'warning',
       (SELECT COUNT(*) FROM stg_assessments WHERE due_day IS NULL),
       'Mostly final exams; sorted last';
