"""Generate a small fake dataset with the same files, columns and quirks as OULAD.

Used to test the pipeline without the real download:
    python scripts/make_sample_data.py data/sample
    python pipeline.py --raw data/sample --out data/sample_tableau --db data/sample.duckdb
"""

import csv
import random
import sys
from pathlib import Path

random.seed(7)
out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/sample")
out.mkdir(parents=True, exist_ok=True)

MODULES = ["AAA", "BBB", "CCC", "DDD"]
PRESENTATIONS = ["2013J", "2014B", "2014J"]
IMD = ["0-10%", "10-20", "20-30%", "30-40%", "40-50%", "50-60%", "60-70%", "70-80%", "80-90%", "90-100%", ""]
AGE = ["0-35", "35-55", "55<="]
EDU = ["No Formal quals", "Lower Than A Level", "A Level or Equivalent", "HE Qualification", "Post Graduate Qualification"]


def write(name, header, rows):
    with open(out / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


courses, assessments, vle, info, reg, sa, svle = [], [], [], [], [], [], []
aid, site, sid = 1000, 5000, 1
for m in MODULES:
    for p in PRESENTATIONS:
        length = random.choice([240, 262, 269])
        courses.append([m, p, length])
        run_assessments = []
        for i, day in enumerate([19, 54, 110, 166, 215]):
            assessments.append([m, p, aid, "TMA" if i % 2 == 0 else "CMA", day, 20])
            run_assessments.append((aid, day))
            aid += 1
        assessments.append([m, p, aid, "Exam", "", 100])
        sites = list(range(site, site + 20))
        site += 20
        for s in sites:
            vle.append([s, m, p, random.choice(["resource", "oucontent", "forumng", "quiz"]), "", ""])
        for _ in range(150):
            imd_i = random.randrange(len(IMD))
            edu_i = random.randrange(len(EDU))
            engagement = random.random() * (0.6 + 0.04 * imd_i + 0.08 * edu_i)
            outcome = random.random()
            if engagement < 0.25 and outcome < 0.7:
                result = "Withdrawn"
            elif engagement < 0.45 and outcome < 0.5:
                result = "Fail"
            elif engagement > 0.8 and outcome < 0.4:
                result = "Distinction"
            else:
                result = random.choice(["Pass", "Pass", "Fail", "Withdrawn"])
            info.append([m, p, sid, random.choice("MF"), "Region", EDU[edu_i], IMD[imd_i],
                         random.choice(AGE), random.choice([0, 0, 0, 1]), 60, random.choice("NY"), result])
            last_day = length
            unreg = ""
            if result == "Withdrawn":
                last_day = random.randint(-20, length - 30)
                unreg = last_day if random.random() > 0.1 else ""
            reg.append([m, p, sid, random.randint(-120, 0), unreg])
            for a, day in run_assessments:
                if day > last_day or random.random() > 0.3 + engagement:
                    continue
                score = "?" if random.random() < 0.01 else min(100, int(40 + engagement * 60 + random.gauss(0, 12)))
                if score != "?":
                    score = max(0, score)
                sa.append([a, sid, day + random.choice([-3, -1, 0, 2, 6]), 0, score])
            for day in range(-10, max(last_day, -9), 3):
                if random.random() < engagement:
                    svle.append([m, p, sid, random.choice(sites), day, random.randint(1, 8)])
            sid += 1

write("courses.csv", ["code_module", "code_presentation", "module_presentation_length"], courses)
write("assessments.csv", ["code_module", "code_presentation", "id_assessment", "assessment_type", "date", "weight"], assessments)
write("vle.csv", ["id_site", "code_module", "code_presentation", "activity_type", "week_from", "week_to"], vle)
write("studentInfo.csv", ["code_module", "code_presentation", "id_student", "gender", "region", "highest_education",
                          "imd_band", "age_band", "num_of_prev_attempts", "studied_credits", "disability", "final_result"], info)
write("studentRegistration.csv", ["code_module", "code_presentation", "id_student", "date_registration", "date_unregistration"], reg)
write("studentAssessment.csv", ["id_assessment", "id_student", "date_submitted", "is_banked", "score"], sa)
write("studentVle.csv", ["code_module", "code_presentation", "id_student", "id_site", "date", "sum_click"], svle)
print(f"Wrote sample OULAD files to {out} ({len(info):,} enrollments, {len(svle):,} click rows)")
