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
        self._response[
            "Content-Disposition"
        ] = "attachment; filename=" + "{}_{}_{}.csv".format(
            filename,
            course.title.replace(" ", "-"),
            timezone.localtime().strftime("%Y-%m-%dT%H%M"),
        )

        self._writer = csv.writer(self._response, delimiter=",")

    def write(self, line):
        self._writer.writerow(line)


class LogWriter(Writer):
    """Writer for exporting logs to a plain text file response"""

    def __init__(self, filename, course):
        super().__init__("text/plain")
        self._response[
            "Content-Disposition"
        ] = "attachment; filename=" + "{}_{}_{}.txt".format(
            filename,
            course.title.replace(" ", "-"),
            timezone.localtime().strftime("%Y-%m-%dT%H%M"),
        )

        self._writer = self._response

    def write(self, line):
        self._writer.write(line)


def course_log(course):
    log_writer = LogWriter("Log", course)

    try:
        log_file_names = sorted(os.listdir(settings.LOG_DIR))
    except FileNotFoundError:
        return log_writer.get_response()

    for log_file_name in log_file_names:
        with open(os.path.join(settings.LOG_DIR, log_file_name)) as f:
            lines = f.readlines()
            for line in lines:
                res = re.search(r"\[(.*?)\]", line)
                if res.group(1) == str(course):
                    log_writer.write(line)

    return log_writer.get_response()


def students_csv(course, students):
    """Creates csv response for percentage list"""

    csv_writer = CSVWriter("Students", course)

    assessments = [assessment for assessment in course.assessment_set.all()]
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


def grades_csv(course, students, groups):
    """Creates csv response for final grade list"""

    csv_writer = CSVWriter("Grades", course)

    assessments = [assessment for assessment in course.assessment_set.all()]

    titles = []
    for assessment in assessments:
        titles.append(
            f"{assessment.title} ({grader.get_group_weight(groups, assessment.group)}%)"
        )
        titles.append(f"{assessment.title} (Chosen %)")

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
        default_total = grader.get_default_total(groups, student)

        if override_total is not None:
            values.append(round(override_total, 2))
            values.append(round(default_total, 2))
            diff = override_total - default_total
            values.append(round(diff, 2))
            values.append("Yes")
        else:
            values.append(round(default_total, 2))
            values.append(round(default_total, 2))
            values.append("")
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

    assessments = [assessment for assessment in course.assessment_set.all()]
    header = ("Assessment", "Default", "Minimum", "Maximum")

    csv_writer.write(header)

    for assessment in assessments:
        values = (assessment.title, assessment.default, assessment.min, assessment.max)
        csv_writer.write(values)

    return csv_writer.get_response()
