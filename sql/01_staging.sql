-- Load the seven raw OULAD files as typed staging tables.
-- Everything is read as text first so that '?' and blanks become NULL
-- through TRY_CAST instead of failing the load.

CREATE OR REPLACE TABLE stg_courses AS
SELECT
    code_module,
    code_presentation,
    TRY_CAST(module_presentation_length AS INTEGER) AS course_length_days,
    -- 2013J -> 2013, J (October start); 2014B -> 2014, B (February start)
    TRY_CAST(LEFT(code_presentation, 4) AS INTEGER)  AS start_year,
    CASE RIGHT(code_presentation, 1) WHEN 'B' THEN 'February' WHEN 'J' THEN 'October' END AS start_month
FROM read_csv('{raw}/courses.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE stg_assessments AS
SELECT
    code_module,
    code_presentation,
    TRY_CAST(id_assessment AS INTEGER) AS id_assessment,
    assessment_type,                                   -- TMA (tutor marked), CMA (computer marked), Exam
    TRY_CAST(NULLIF(date, '?') AS INTEGER) AS due_day, -- days from course start; NULL for most final exams
    TRY_CAST(weight AS DOUBLE) AS weight
FROM read_csv('{raw}/assessments.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE stg_vle AS
SELECT
    TRY_CAST(id_site AS INTEGER) AS id_site,
    code_module,
    code_presentation,
    activity_type
FROM read_csv('{raw}/vle.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE stg_student_info AS
SELECT
    code_module,
    code_presentation,
    TRY_CAST(id_student AS INTEGER) AS id_student,
    gender,
    region,
    highest_education,
    -- The raw file labels one band '10-20' while every other band ends in '%'.
    CASE
        WHEN imd_band IS NULL OR imd_band IN ('', '?') THEN 'Unknown'
        WHEN imd_band = '10-20' THEN '10-20%'
        ELSE imd_band
    END AS imd_band,
    age_band,
    TRY_CAST(num_of_prev_attempts AS INTEGER) AS num_of_prev_attempts,
    TRY_CAST(studied_credits AS INTEGER) AS studied_credits,
    disability,
    final_result
FROM read_csv('{raw}/studentInfo.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE stg_student_registration AS
SELECT
    code_module,
    code_presentation,
    TRY_CAST(id_student AS INTEGER) AS id_student,
    TRY_CAST(NULLIF(date_registration, '?') AS INTEGER)   AS registration_day,
    TRY_CAST(NULLIF(date_unregistration, '?') AS INTEGER) AS unregistration_day
FROM read_csv('{raw}/studentRegistration.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE stg_student_assessment AS
SELECT
    TRY_CAST(id_assessment AS INTEGER) AS id_assessment,
    TRY_CAST(id_student AS INTEGER) AS id_student,
    TRY_CAST(date_submitted AS INTEGER) AS submitted_day,
    TRY_CAST(is_banked AS INTEGER) = 1 AS is_banked,   -- result carried over from an earlier attempt
    TRY_CAST(NULLIF(score, '?') AS DOUBLE) AS score
FROM read_csv('{raw}/studentAssessment.csv', header = true, all_varchar = true);

-- studentVle is the 10M-row click log. Typed columns are given up front so
-- DuckDB does not have to sniff it, and it never leaves the database.
CREATE OR REPLACE TABLE stg_student_vle AS
SELECT *
FROM read_csv(
    '{raw}/studentVle.csv',
    header = true,
    columns = {
        'code_module': 'VARCHAR',
        'code_presentation': 'VARCHAR',
        'id_student': 'INTEGER',
        'id_site': 'INTEGER',
        'date': 'INTEGER',
        'sum_click': 'INTEGER'
    }
);
