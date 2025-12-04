import csv
import os
import re
from datetime import datetime
from abc import ABC, abstractmethod
from decimal import Decimal

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

from bs4 import BeautifulSoup
from flexible_assessment.models import FlexAssessment

from . import grader


class Writer(ABC):
    @abstractmethod
    def __init__(self, response_type):
        self._response = HttpResponse(content_type=response_type)

    @abstractmethod
    def write(self):
        pass

    def get_response(self):
        return self._response


class CSVWriter(Writer):
    """Writer for exporting tables and forms to a csv response"""

    def __init__(self, filename, course):
        super().__init__("text/csv")
        self._response["Content-Disposition"] = (
            "attachment; filename="
            + "{}_{}_{}.csv".format(
                filename,
                course.title.replace(" ", "-"),
                timezone.localtime().strftime("%Y-%m-%dT%H%M"),
            )
        )

        self._writer = csv.writer(self._response, delimiter=",")

    def write(self, line):
        self._writer.writerow(line)


def parse_timestamp(line):
    """Extracts timestamp from log line, assuming format 'YYYY-MM-DD HH:MM:SS[,.]mmm'."""
    match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,.]\d{3}", line)
    if match:
        timestamp_str = match.group().replace(",", ".")
        return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
    return None  # Return None if no timestamp is found


def course_log(course):
    csv_writer = CSVWriter("Log", course)

    # list of tuples (timestamp, line)
    logs = []

    try:
        log_file_names = sorted(os.listdir(settings.LOG_DIR))
    except FileNotFoundError:
        return csv_writer.get_response()

    # Set to keep track of seen lines to avoid duplicates
    seen_lines = set()

    for log_file_name in log_file_names:
        with open(os.path.join(settings.LOG_DIR, log_file_name)) as f:
            lines = f.readlines()
            for line in lines:
                res = re.search(r"\[(.*?)\]", line)
                if res and res.group(1) == str(course) and line not in seen_lines:
                    seen_lines.add(line)
                    timestamp = parse_timestamp(line)
                    logs.append((timestamp, line))

    # sort logs by timestamp
    logs.sort(key=lambda x: x[0], reverse=True)

    first_row = ["Course"] + ["Time"] + ["Message"] + ["User"]
    csv_writer.write(first_row)

    for log in logs:

        pattern_full = (
            r"\[(.*?)\] - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (.*?) \| (.*)"
        )

        pattern_partial = (
            r"\[(.*?)\] - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (.*)"
        )

        match_full = re.match(pattern_full, log[1])
        match_partial = re.match(pattern_partial, log[1])

        line = None

        if match_full:
            course, timestamp, message, user = match_full.groups()
            line = [course, timestamp, message, user]
        elif match_partial:
            course, timestamp, message = match_partial.groups()
            line = [course, timestamp, message]
        else:
            line = [f"Failed to match pattern: {log[1]}"]

        csv_writer.write(line)

    return csv_writer.get_response()


def students_csv(course, students):
    """Creates csv response for percentage list"""

    csv_writer = CSVWriter("Students", course)

    assessments = list(course.assessment_set.all().order_by("order"))

    header = (
        ["Student"]
        + ["Chose Percentages"]
        + [assessment.title for assessment in assessments]
        + ["Comments"]
    )

    csv_writer.write(header)

    for student in students:
        values = []
        values.append("{}, {}".format(student.display_name, student.login_id))

        # if first flex doens't exist, student didn't choose flexes
        first_flex = student.flexassessment_set.get(assessment=assessments[0]).flex
        if first_flex is None:
            values.append("No")
        else:
            values.append("Yes")

        for assessment in assessments:
            flex = student.flexassessment_set.get(assessment=assessment).flex
            if flex is None:
                flex = assessment.default
            values.append(flex)

        comment = student.usercomment_set.get(course=course).comment
        # if comment == "":
        #    comment = "no comment entered for " + str(student.display_name)
        values.append(comment)

        csv_writer.write(values)

    return csv_writer.get_response()


from decimal import Decimal, ROUND_HALF_UP


def round_half_up(value, digits=2):
    if value is None:
        return None
    """Rounds a float to the specified number of digits using ROUND_HALF_UP"""
    d = Decimal(str(value))  # Convert to Decimal
    return d.quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP)

# def grades_csv(course, students, groups):
#     """Creates csv response for final grade list"""

#     csv_writer = CSVWriter("Grades", course)

#     assessments = list(course.assessment_set.all().order_by("order"))

#     titles = []
#     for assessment in assessments:
#         titles.append(f"{assessment.title} Grade %")
#         titles.append(
#             f"{assessment.title} Weight % ({grader.get_group_weight(groups, assessment.group)}%)"
#         )

#     header = (
#         ["Student"]
#         + ["Override Total", "Default Total", "Difference", "Chose Percentages?"]
#         + titles
#     )

#     csv_writer.write(header)

#     for student in students:
#         values = []
#         values.append("{}, {}".format(student.display_name, student.login_id))

#         override_total = grader.get_override_total(groups, student, course)
#         override_total = round_half_up(override_total, 3)
#         default_total = grader.get_default_total(groups, student)
#         default_total = round_half_up(default_total, 3)

#         if override_total is not None:
#             values.append(round_half_up(override_total, 2))
#             values.append(round_half_up(default_total, 2))
#             diff = override_total - default_total
#             values.append(round_half_up(diff, 2))
#             values.append("Yes")
#         else:
#             values.append(round_half_up(default_total, 2))
#             values.append(round_half_up(default_total, 2))
#             values.append("0")
#             values.append("No")

#         for assessment in assessments:
#             score = grader.get_score(groups, assessment.group, student)
#             values.append(score)

#             group_weight = grader.get_group_weight(groups, assessment.group)

#             flex = student.flexassessment_set.get(assessment=assessment).flex
#             values.append(flex) if flex is not None else values.append(group_weight)

#         csv_writer.write(values)

#     csv_writer.write(["Average Override", "Average Default", "Average Difference"])

#     csv_writer.write(grader.get_averages(groups, course))

#     return csv_writer.get_response()


# def grades_csv(course, html):
#     """Creates csv response for final grade list"""

#     csv_writer = CSVWriter("Grades", course)

#     soup = BeautifulSoup(html, "html.parser")
#     table = soup.find("table", {"id": "final"})
    
#     if table is None:
#         return csv_writer.get_response() 

#     thead = table.thead
#     if thead:
#         header_cells = thead.find_all("th", recursive=True)
#         values = [cell.get_text(" ", strip=True) for cell in header_cells[:-1]]
#         csv_writer.write(values)

#     tbody = table.tbody
#     if tbody:
#         for row in tbody.find_all("tr", recursive=False):
#             cells = row.find_all("td", recursive=False)
#             if not cells:
#                 continue

#             name = cells[0].get_text(" ", strip=True)
#             cwl = cells[-1].get_text(" ", strip=True)

#             values = [f"{name}, {cwl}"]
#             values.extend(
#                 cell.get_text(" ", strip=True) for cell in cells[1:-1]
#             )
#             csv_writer.write(values)

#     tfoot = table.tfoot
#     if tfoot:
#         csv_writer.write(["Average Override", "Average Default", "Average Difference"])
#         footer_cells = tfoot.find_all("td", recursive=True)
#         values = [cell.get_text(" ", strip=True) for cell in footer_cells]
#         csv_writer.write(values)
#     return csv_writer.get_response()


def grades_csv(course, students, groups):
    """Creates csv response for final grade list"""

    csv_writer = CSVWriter("Grades", course)

    assessments = list(
        course.assessment_set.all().order_by("order", "id")
    )

    student_ids = [s.user_id for s in students]

    flex_qs = (
        FlexAssessment.objects
        .filter(assessment__course=course, user__user_id__in=student_ids)
        .select_related("assessment", "user")
    )

    flex_by_student_assessment = {}
    for fa in flex_qs:
        key = (fa.user_id, fa.assessment_id)
        flex_by_student_assessment[key] = fa.flex  

    score_by_student_group = {}
    weight_by_group = {}

    for group_id_str, data in groups.items():
        group_weight = Decimal(str(data["group_weight"]))
        weight_by_group[group_id_str] = group_weight

        for student_id_str, score in data["grade_list"]["grades"]:
            sid = int(student_id_str)
            key = (sid, group_id_str)
            score_by_student_group[key] = (
                None if score is None else Decimal(str(score))
            )

    def compute_default_total(student_id: int) -> Decimal:
        scores = []
        weights = []
        for group_id_str, group_weight in weight_by_group.items():
            score = score_by_student_group.get((student_id, group_id_str))
            if score is not None:
                scores.append(score)
                weights.append(group_weight)

        if not weights:
            return Decimal("0")

        overall = Decimal("0")
        for score, weight in zip(scores, weights):
            overall += score * weight / Decimal("100")

        total_weight = sum(weights)
        if total_weight == 0:
            return Decimal("0")

        overall = overall / total_weight * Decimal("100")
        return overall

    def compute_override_total_and_flag(student_id: int):
        flex_values = []
        flex_sum = Decimal("0")
        has_null = False

        assessment_scores = []
        assessment_weights = []

        for assessment in assessments:
            fa_flex = flex_by_student_assessment.get((student_id, assessment.id))
            if fa_flex is None:
                has_null = True
            else:
                flex_values.append(Decimal(fa_flex))
                flex_sum += Decimal(fa_flex)

            group_id_str = str(assessment.group)
            score = score_by_student_group.get((student_id, group_id_str))
            if score is not None:
                assessment_scores.append(score)
                if fa_flex is not None:
                    assessment_weights.append(Decimal(fa_flex))

        is_valid = (not has_null) and (flex_sum == Decimal("100"))

        if not is_valid:
            return None, False  

        if not assessment_scores or not assessment_weights:
            return Decimal("0"), True

        overall = Decimal("0")
        for score, weight in zip(assessment_scores, assessment_weights):
            overall += score * weight / Decimal("100")

        total_flex = sum(assessment_weights)
        if total_flex == 0:
            return Decimal("0"), True

        overall = overall / total_flex * Decimal("100")
        return overall, True  


    default_totals = {}
    override_totals = {}
    chose_flex_flag = {}  

    for s in students:
        sid = s.user_id
        default_totals[sid] = compute_default_total(sid)
        override, chose = compute_override_total_and_flag(sid)

        if override is None:
            override_totals[sid] = default_totals[sid]
        else:
            override_totals[sid] = override

        chose_flex_flag[sid] = chose

    titles = []
    for assessment in assessments:
        titles.append(f"{assessment.title} Grade %")
        titles.append(
            f"{assessment.title} Weight % ({grader.get_group_weight(groups, assessment.group)}%)"
        )

    header = (
        ["Student"]
        + ["Override Total", "Default Total", "Difference", "Chose Percentages?"]
        + titles
    )
    csv_writer.write(header)

    for student in students:
        sid = student.user_id

        values = []
        values.append(f"{student.display_name}, {student.login_id}")

        default_total = default_totals[sid]
        override_total = override_totals[sid]
        diff = override_total - default_total

        values.append(round_half_up(override_total, 2))
        values.append(round_half_up(default_total, 2))
        values.append(round_half_up(diff, 2))
        values.append("Yes" if chose_flex_flag[sid] else "No")

        for assessment in assessments:
            group_id_str = str(assessment.group)
            score = score_by_student_group.get((sid, group_id_str))
            values.append(
                round_half_up(score, 2) if score is not None else None
            )

            fa_flex = flex_by_student_assessment.get((sid, assessment.id))
            if fa_flex is not None:
                values.append(str(round_half_up(fa_flex, 2)))
            else:
                gw = grader.get_group_weight(groups, assessment.group)
                values.append(f"{gw:.2f}%" if gw != "" else "")

        csv_writer.write(values)


    csv_writer.write(["Average Override", "Average Default", "Average Difference"])

    overrides_list = list(override_totals.values())
    defaults_list = list(default_totals.values())
    diffs_list = [o - d for o, d in zip(overrides_list, defaults_list)]

    def avg_or_zero(nums):
        return (
            round_half_up(sum(nums) / len(nums), 2) if nums else Decimal("0")
        )

    csv_writer.write(
        [
            avg_or_zero(overrides_list),
            avg_or_zero(defaults_list),
            avg_or_zero(diffs_list),
        ]
    )

    return csv_writer.get_response()
