import csv
import os
import re
from abc import ABC, abstractmethod

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

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


class LogWriter(Writer):
    """Writer for exporting logs as a csv response"""

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

        self._writer = self._response

    def write(self, line):
        self._writer.write(line)


from datetime import datetime


def parse_timestamp(line):
    """Extracts timestamp from log line, assuming format 'YYYY-MM-DD HH:MM:SS,mmm'."""
    match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}", line)
    if match:
        return datetime.strptime(match.group(), "%Y-%m-%d %H:%M:%S,%f")
    return None  # Return None if no timestamp is found


def course_log(course):
    log_writer = LogWriter("Log", course)

    # list of tuples (timestamp, line)
    logs = []

    try:
        log_file_names = sorted(os.listdir(settings.LOG_DIR))
    except FileNotFoundError:
        return log_writer.get_response()

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

    log_writer.write("Course, Time, Message, User\n")

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
            line = f'"{course}", "{timestamp}", "{message}", "{user}"\n'
        elif match_partial:
            course, timestamp, message = match_partial.groups()
            line = f'"{course}", "{timestamp}", "{message}", ""\n'
        else:
            line = f"Failed to match pattern: {log[1]}"

        log_writer.write(line)

    return log_writer.get_response()


def students_csv(course, students):
    """Creates csv response for percentage list"""

    csv_writer = CSVWriter("Students", course)

    assessments = list(course.assessment_set.all().order_by("order"))

    header = (
        ["Student"] + [assessment.title for assessment in assessments] + ["Comment"]
    )

    csv_writer.write(header)

    for student in students:
        values = []
        values.append("{}, {}".format(student.display_name, student.login_id))

        for assessment in assessments:
            flex = student.flexassessment_set.get(assessment=assessment).flex
            values.append(flex)

        comment = student.usercomment_set.get(course=course).comment
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


def grades_csv(course, students, groups):
    """Creates csv response for final grade list"""

    csv_writer = CSVWriter("Grades", course)

    assessments = list(course.assessment_set.all().order_by("order"))

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
        values = []
        values.append("{}, {}".format(student.display_name, student.login_id))

        override_total = grader.get_override_total(groups, student, course)
        override_total = round_half_up(override_total, 3)
        default_total = grader.get_default_total(groups, student)
        default_total = round_half_up(default_total, 3)

        if override_total is not None:
            values.append(round_half_up(override_total, 2))
            values.append(round_half_up(default_total, 2))
            diff = override_total - default_total
            values.append(round_half_up(diff, 2))
            values.append("Yes")
        else:
            values.append(round_half_up(default_total, 2))
            values.append(round_half_up(default_total, 2))
            values.append("0")
            values.append("No")

        for assessment in assessments:
            score = grader.get_score(groups, assessment.group, student)
            values.append(score)

            group_weight = grader.get_group_weight(groups, assessment.group)

            flex = student.flexassessment_set.get(assessment=assessment).flex
            values.append(flex) if flex is not None else values.append(group_weight)

        csv_writer.write(values)

    csv_writer.write(["Average Override", "Average Default", "Average Difference"])

    csv_writer.write(grader.get_averages(groups, course))

    return csv_writer.get_response()


def assessments_csv(course):
    """Creates csv response for course assessments"""

    csv_writer = CSVWriter("Assessments", course)

    assessments = list(course.assessment_set.all().order_by("order"))
    header = ("Assessment", "Default", "Minimum", "Maximum")

    csv_writer.write(header)

    for assessment in assessments:
        values = (assessment.title, assessment.default, assessment.min, assessment.max)
        csv_writer.write(values)

    return csv_writer.get_response()
