# Dashboard 1: Course Outcomes Overview

**Question it answers:** Which courses have high withdrawal or low pass rates, and is it getting better or worse?

**What you learn in Tableau:** connecting to CSVs, dimensions vs. measures, calculated fields, KPI tiles, a highlight table, a parameter, filters, and assembling a dashboard with an action.

**Data:** `fact_enrollment.csv` (one row per student per course run, 32,593 rows). The other five CSVs are for Dashboards 2 to 4, but connecting them now saves time later.

Time: about 90 minutes the first time.

---

## 0. Get the files onto your computer (5 min)

1. Download the six CSVs (`fact_enrollment.csv`, `agg_weekly_engagement.csv`, `agg_withdrawal_timing.csv`, `agg_assessment_performance.csv`, `agg_equity_gaps.csv`, `data_quality_checks.csv`). Either run `python pipeline.py` (see the README) and use `data/tableau/`, or download the zip of them if someone shared one.
2. Put them in one folder you will not move later, for example `Documents\Tableau\oulad` (Windows) or `~/Documents/Tableau/oulad` (Mac). Tableau remembers the folder path, so moving the files later breaks the connection.

> **Shortcut:** `scripts/build_workbook.py` builds `Online Learning Outcomes.twbx`, a packaged workbook with all six CSVs connected and this dashboard already built. Open it in Tableau Public with **File > Open** to see the finished result, then build your own copy with the steps below. Building it yourself is what makes you able to talk about it in an interview.

## 1. Connect to the data (10 min)

1. Open **Tableau Public**. On the start page, under **Connect > To a File**, click **Text file** and pick `fact_enrollment.csv`.
2. You are now on the **Data Source** page. At the bottom is a preview grid with a small type icon above each column (Abc = text, # = number, T|F = true/false).
3. Fix three types. Click the **#** icon and choose **String** for:
   - `id_student`: it is an ID, adding IDs together makes no sense.
   - `start_year`: a label (2013, 2014), not a quantity.
   - `early_engagement_quartile`: a rank from 1 to 4.
4. Check that `is_first_attempt`, `submitted_first_assessment` and `withdrew_before_start` show **T|F**. If one shows **Abc**, change it to **Boolean**.
5. Leave `is_pass`, `is_withdrawn`, `is_distinction`, `is_fail` as **#** numbers. They are 0/1 flags and their average is a rate.
6. Optional, for later dashboards: in the left pane under **Connections**, click **Add**, choose **Text file**, and add each of the other five CSVs as its own connection. Do not drag them onto the canvas next to `fact_enrollment`; they are separate tables at different grains and joining them would duplicate rows.
7. Click **Sheet 1** at the bottom left.

> **Field names:** newer versions of Tableau tidy names, so `code_module` may show as **Code Module**. Use whatever the Data pane shows. When you type a formula, Tableau autocompletes field names.

> **Concept:** the Data pane splits fields into **Dimensions** (things you slice by, like `code_module`) and **Measures** (numbers you aggregate, like `is_pass`). Blue pills are discrete, green pills are continuous.

## 2. Create the core calculated fields (10 min)

Click the small triangle at the top of the Data pane (or right-click empty space in it) > **Create Calculated Field**. Make each of these:

| Name | Formula | Format |
| --- | --- | --- |
| `Enrollments` | `COUNT([id_student])` | Number, 0 decimals, thousands separator |
| `Pass Rate` | `AVG([is_pass])` | Percentage, 1 decimal |
| `Withdrawal Rate` | `AVG([is_withdrawn])` | Percentage, 1 decimal |
| `Distinction Rate` | `AVG([is_distinction])` | Percentage, 1 decimal |
| `First-Attempt Pass Rate` | `AVG(IF [is_first_attempt] THEN [is_pass] END)` | Percentage, 1 decimal |

To format: right-click the new field in the Data pane > **Default Properties > Number Format > Percentage**, decimals 1.

`is_pass` is 1 for both Pass and Distinction, so Pass Rate counts both, which matches how the Open University reports it.

> **Interview line:** "I define rates as the average of a 0/1 flag. The logic lives in one place and it rolls up correctly at any level, course, term or student group."

## 3. Build the KPI tiles (15 min)

Make one sheet per KPI. For the first:

1. Double-click the **Sheet 1** tab and rename it **KPI Pass Rate**.
2. Drag `Pass Rate` onto **Text** on the Marks card.
3. Click **Text > ...** (the three dots). Above the field, type `Pass rate` in small grey text, then put the field on its own line in 28 pt bold.
4. Right-click the sheet title > **Hide Title** if you want a cleaner tile.

Right-click the sheet tab > **Duplicate**, then swap the measure for each of: `Withdrawal Rate`, `Distinction Rate`, `First-Attempt Pass Rate`, `Enrollments`.

**Checkpoint (all students):** Enrollments 32,593, Pass rate 47.2%, Withdrawal rate 31.2%, Distinction rate 9.3%, First-attempt pass rate 49.3%. If yours differ, check the data types from step 1.

## 4. Build the course-by-term highlight table (15 min)

New sheet (the icon right of the last tab), name it **Course Matrix**.

1. Drag `code_module` to **Rows**.
2. Drag `code_presentation` to **Columns**. They sort as 2013B, 2013J, 2014B, 2014J, which is also date order (B starts in February, J in October).
3. Drag `Withdrawal Rate` to **Color**, then drag it again onto **Text**.
4. In the **Marks** dropdown (it says Automatic), choose **Square**. This makes it a highlight table.
5. Click **Color > Edit Colors**, pick a sequential palette such as **Orange**, and tick **Use Full Color Range**.
6. Drag `Enrollments` onto **Tooltip** so hovering shows the class size.

Some cells are blank. That is real: not every course ran every term (CCC only ran in 2014, AAA only in the October terms). Say so if asked, and do not fill blanks with zero.

**Checkpoint:** CCC is the darkest row (46.4% in 2014B, 43.1% in 2014J). GGG 2013J is the lightest cell at 6.9%.

> **Concept:** a highlight table is the fastest way for a program lead to see where to look. Dark cells are where to dig in.

## 5. Add a parameter to switch the metric (15 min)

This lets the viewer pick which outcome the matrix shows.

1. Data pane triangle > **Create Parameter**. Name `Choose Metric`, data type **String**, allowable values **List**, and add `Pass Rate`, `Withdrawal Rate`, `Distinction Rate`. Set the current value to `Withdrawal Rate`.
2. Create a calculated field `Selected Metric`:
   ```
   CASE [Choose Metric]
     WHEN 'Pass Rate' THEN [Pass Rate]
     WHEN 'Withdrawal Rate' THEN [Withdrawal Rate]
     WHEN 'Distinction Rate' THEN [Distinction Rate]
   END
   ```
   Format it as a percentage with 1 decimal.
3. On **Course Matrix**, drag `Selected Metric` onto the `Withdrawal Rate` pills on Color and on Text to replace them.
4. Right-click `Choose Metric` in the Parameters section > **Show Parameter**. Switch it and watch the matrix change.

> **Interview line:** "A parameter plus a CASE field lets one chart answer three questions, so the dashboard stays small."

## 6. Add a trend by term (10 min)

New sheet, name it **Trend**.

1. `code_presentation` to **Columns**, `Selected Metric` to **Rows**.
2. `code_module` to **Color**. Marks type: **Line**.
3. Courses that ran only once or twice show short lines or single dots. That is expected.

## 7. Filters (10 min)

**Exclude students who withdrew before the course started.** 2,678 enrollments withdrew before day 0; the course itself cannot have influenced them.

1. On **Course Matrix**, drag `withdrew_before_start` to **Filters**, tick **False** only, click OK.
2. Right-click the pill on Filters > **Apply to Worksheets > All Using This Data Source**. It now applies to every sheet, KPIs included.

**Checkpoint (excluding pre-start withdrawals):** Enrollments 29,915, Pass rate 51.4%, Withdrawal rate 25.0%, Distinction rate 10.1%, First-attempt pass rate 53.6%.

**Add viewer filters.** Drag `age_band`, `imd_band` and `highest_education` to Filters, keep **All** selected, then right-click each > **Show Filter**, and apply each to **All Using This Data Source** the same way.

> **Interview line:** "Withdrawal rate drops from 31% to 25% once you exclude people who left before day one. I show it both ways, because a program team and a marketing team ask different questions."

## 8. Assemble the dashboard (15 min)

1. Click the **New Dashboard** icon at the bottom (second icon after the tabs).
2. On the left, **Size**: Fixed, 1200 x 800.
3. Drag a **Horizontal** object from the Objects list to the top, then drop the five KPI sheets into it side by side.
4. Drop **Course Matrix** below on the left and **Trend** to its right.
5. Make sure the `Choose Metric` parameter and the three filters sit in a column on the right. If one is missing, click the sheet on the dashboard, open its dropdown arrow, and choose it under **Parameters** or **Filters**.
6. Drag a **Text** object to the very top: title *Course Outcomes Overview*, subtitle *Open University, 2013 to 2014. Pick a metric to see which courses need attention.*
7. **Dashboard > Actions > Add Action > Filter**: source sheet **Course Matrix**, target **Trend**, run on **Select**, clearing the selection shows all values. Clicking a cell now filters the trend to that course.

## 9. Save and publish

Tableau Public saves to the web, not to your computer. **File > Save to Tableau Public As...**, sign in if asked, name it `Online Learning Outcomes`. It opens in your browser when done. Everything on Tableau Public is public, which is fine here because OULAD is an open, anonymized dataset. Copy the link into the README under **Dashboards**.

---

## What the real data says

All figures exclude the 2,678 enrollments that withdrew before the course started.

- **CCC is the problem course.** Highest withdrawal (38.1%) and lowest pass rate (42.3%) of the seven. DDD is second on both (30.1%, 45.3%).
- **Withdrawal is rising.** Across all courses it went from 20.6% in the October 2013 cohort to 28.3% in October 2014. FFF went from 21.3% to 30.4% across its four runs.
- **GGG has the lowest withdrawal but it tripled**, from 4.7% (2013J) to 14.5% (2014J). Low and rising is worth a question before it becomes high.
- **AAA has the best pass rate** at 72.9%, though it is small (748 enrollments over two runs).
- **First attempts pass far more often:** 49.3% vs. 33.1% for students repeating the course (all enrollments). A hook for Dashboard 4.

## What to say about it in the interview

- **The story:** "CCC loses almost four in ten students who actually start it, and withdrawal is climbing across the catalog, up about eight points in a year. CCC is where I'd start a conversation with the program team, and I'd want to know what changed between the 2013 and 2014 cohorts."
- **Design choice:** "The KPIs answer 'how are we doing', the matrix answers 'where', and the trend answers 'is it changing'. That's the order a director reads in."
- **Data choice:** "I excluded students who withdrew before the course started, because course design can't have influenced them. The blank cells are courses that didn't run that term, and I left them blank rather than showing zero."
