# Dashboard 1: Course Outcomes Overview

**Question it answers:** Which courses have high withdrawal or low pass rates, and is it getting better or worse?

**What you learn in Tableau:** connecting to a CSV, dimensions vs. measures, calculated fields, KPI tiles, a highlight table, filters, a parameter, and assembling a dashboard.

**Data:** `data/tableau/fact_enrollment.csv` (one row per student per course run).

Time: about 90 minutes the first time.

---

## 1. Connect to the data (5 min)

1. Open **Tableau Public** (the free desktop app).
2. Under **Connect > To a File**, click **Text file** and pick `fact_enrollment.csv`.
3. On the Data Source page, check the field types on the column headers:
   - `id_student`, `start_year`, `early_engagement_quartile`: click the type icon and change to **String** (they are labels, not numbers to add up).
   - `is_pass`, `is_withdrawn`, `is_distinction`, `is_fail`: leave as **Number (whole)**. Their average is a rate.
   - `is_first_attempt`, `submitted_first_assessment`, `withdrew_before_start`: should show as **Boolean** (T|F).
4. Click **Sheet 1** at the bottom.

> **Concept:** Tableau splits fields into **Dimensions** (blue, things you slice by, like `code_module`) and **Measures** (green, numbers you aggregate, like `is_pass`). Blue = discrete, green = continuous.

## 2. Create the core calculated fields (10 min)

Right-click in the Data pane > **Create Calculated Field**. Make each of these:

| Name | Formula | Format |
| --- | --- | --- |
| `Enrollments` | `COUNT([id_student])` | Number, 0 decimals |
| `Pass Rate` | `AVG([is_pass])` | Percentage, 1 decimal |
| `Withdrawal Rate` | `AVG([is_withdrawn])` | Percentage, 1 decimal |
| `Distinction Rate` | `AVG([is_distinction])` | Percentage, 1 decimal |
| `First-Attempt Pass Rate` | `AVG(IF [is_first_attempt] THEN [is_pass] END)` | Percentage, 1 decimal |

To format: right-click the field > **Default Properties > Number Format > Percentage**.

> **Interview line:** "I define rates as the average of a 0/1 flag. It keeps the logic in one place and it rolls up correctly at any level, course, term or student group."

## 3. Build the KPI tiles (20 min)

Make one sheet per KPI. For the first:

1. Rename the sheet **KPI Pass Rate** (double-click the tab).
2. Drag `Pass Rate` onto **Text** on the Marks card.
3. Click **Text > ...** and make the number big (28 pt, bold). Add a second line above it in small grey text: `Pass rate`.
4. On the **Marks** dropdown, keep it as **Text**. Hide the header if one shows.

Right-click the sheet tab > **Duplicate**, then swap the measure for each of: `Withdrawal Rate`, `Distinction Rate`, `First-Attempt Pass Rate`, `Enrollments`.

## 4. Build the course-by-term highlight table (20 min)

New sheet, name it **Course Matrix**.

1. Drag `code_module` to **Rows**.
2. Drag `code_presentation` to **Columns**.
3. Drag `Withdrawal Rate` to **Color**, then also to **Text**.
4. In the **Marks** dropdown, choose **Square**. This turns it into a highlight table.
5. Click **Color > Edit Colors**: pick a sequential palette (e.g. Orange), tick **Use full color range**.
6. Drag `Enrollments` to **Tooltip** so hovering shows the class size.

> **Concept:** a highlight table is the fastest way for a program lead to see where to look. Dark cells are where to dig in.

## 5. Add a parameter to switch the metric (15 min)

This lets the viewer pick which outcome the matrix shows.

1. Data pane > right-click > **Create Parameter**. Name `Choose Metric`, data type **String**, **List** of values: `Pass Rate`, `Withdrawal Rate`, `Distinction Rate`.
2. Create a calculated field `Selected Metric`:
   ```
   CASE [Choose Metric]
     WHEN 'Pass Rate' THEN [Pass Rate]
     WHEN 'Withdrawal Rate' THEN [Withdrawal Rate]
     WHEN 'Distinction Rate' THEN [Distinction Rate]
   END
   ```
   Format it as a percentage.
3. On **Course Matrix**, replace `Withdrawal Rate` on Color and Text with `Selected Metric`.
4. Right-click the parameter > **Show Parameter**.

## 6. Add a trend line by term (10 min)

New sheet, name it **Trend**.

1. `code_presentation` to **Columns**, `Selected Metric` to **Rows**.
2. `code_module` to **Color**. Marks type: **Line**.
3. Right-click `code_presentation` on Columns > **Sort** > alphabetic ascending (2013B, 2013J, 2014B, 2014J is chronological).

## 7. Filters (5 min)

On **Course Matrix**, drag `age_band`, `imd_band` and `highest_education` to **Filters** and pick **All**. Right-click each > **Show Filter**. Later, on the dashboard, set each filter to **Apply to Worksheets > All Using This Data Source**.

Also add `withdrew_before_start` as a filter, set to **False** only, with title "Exclude withdrawals before course start". That matches the data quality note in the README.

## 8. Assemble the dashboard (15 min)

1. Click the **New Dashboard** icon at the bottom.
2. **Size**: Fixed, 1200 x 800.
3. Drag a **Horizontal** container to the top and drop the five KPI sheets into it.
4. Drop **Course Matrix** below on the left, **Trend** on the right.
5. Put the filters and the `Choose Metric` parameter in a column on the right.
6. Add a **Text** object at the top: title *Course Outcomes Overview* and a one-line subtitle, e.g. *Open University, 2013 to 2014. Pick a metric to see which courses need attention.*
7. **Dashboard > Actions > Add Action > Filter**: source **Course Matrix**, target **Trend**, run on **Select**. Clicking a cell now filters the trend line to that course.

## 9. Save and publish

**File > Save to Tableau Public As...**, name it `Online Learning Outcomes`. It will open in your browser. Copy the link into the README under **Dashboards**.

---

## What to say about it in the interview

- **The story:** "Course DDD's withdrawal rate stands out across every term, so that's where I'd start a conversation with the program team." (Replace with what the real data shows.)
- **Design choice:** "The KPIs answer 'how are we doing', the matrix answers 'where', and the trend answers 'is it changing'. That's the order a director reads in."
- **Data choice:** "I excluded students who withdrew before the course started, because course design can't have influenced them."
