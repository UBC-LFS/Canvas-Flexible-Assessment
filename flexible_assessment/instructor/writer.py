import csv
import re
from abc import ABC, abstractmethod

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

from . import grader


class Writer(ABC):
    @property
    @abstractmethod
    def _response(self):
        pass

    @abstractmethod
    def write(self):
        pass

    def get_response(self):
        return self._response


class CSVWriter(Writer):
    """Writer for exporting tables and forms to a csv response"""

    _response = HttpResponse(content_type='text/csv')

    def __init__(self, filename, course):
        self._response['Content-Disposition'] = 'attachment; filename=' \
            + '{}_{}_{}.csv'.format(filename,
                                    course.title.replace(' ', '-'),
                                    timezone.localtime()
                                    .strftime("%Y-%m-%dT%H%M"))

        self._writer = csv.writer(self._response, delimiter=",")

    def write(self, line):
        self._writer.writerow(line)


class LogWriter(Writer):
    """Writer for exporting logs to a plain text file response"""

    _response = HttpResponse(content_type='text/plain')

    def __init__(self, filename, course):
        self._response['Content-Disposition'] = 'attachment; filename=' \
            + '{}_{}_{}.txt'.format(filename,
                                    course.title.replace(' ', '-'),
                                    timezone.localtime()
                                    .strftime("%Y-%m-%dT%H%M"))

        self._writer = self._response

    def write(self, line):
        self._writer.write(line)


def course_log(course):
    log_writer = LogWriter('Log', course)

    with open(settings.LOG_FILE) as f:
        lines = f.readlines()
        for line in lines:
            res = re.search(r'\[(.*?)\]', line)
            if res.group(1) == course.title:
                log_writer.write(line)

    return log_writer.get_response()


def students_csv(course, students):
    """Creates csv response for percentage list"""

    csv_writer = CSVWriter('Students', course)

    assessments = [
        assessment for assessment in course.assessment_set.all()]
    header = ['Student'] + \
        [assessment.title for assessment in assessments] + ['Comment']

    csv_writer.write(header)

    for student in students:
        values = []
        values.append('{}, {}'.format(student.display_name,
                                      student.login_id))

        for assessment in assessments:
            flex = student.flexassessment_set.get(
                assessment=assessment).flex
            values.append(flex)

        comment = student.usercomment_set.get(course=course).comment
        values.append(comment)

        csv_writer.write(values)

    return csv_writer.get_response()


def grades_csv(course, students, groups):
    """Creates csv response for final grade list"""

    csv_writer = CSVWriter('Grades', course)

    assessments = [
        assessment for assessment in course.assessment_set.all()]

    titles = [
        "{} ({}%)".format(
            assessment.title,
            grader.get_group_weight(
                groups,
                assessment.group)) for assessment in assessments]

    header = ['Student'] + titles + \
        ['Override Total', 'Default Total', 'Difference']

    csv_writer.write(header)

    for student in students:
        values = []
        values.append(
            '{}, {}'.format(
                student.display_name,
                student.login_id))

        for assessment in assessments:
            score = grader.get_score(groups, assessment.group, student)
            values.append(score)

        override_total = grader.get_override_total(groups, student, course)
        default_total = grader.get_default_total(groups, student)

        if override_total is not None:
            values.append(round(override_total, 2))
            values.append(round(default_total, 2))
            diff = override_total - default_total
            values.append(round(diff, 2))
        else:
            values.append(round(default_total, 2))
            values.append(round(default_total, 2))
            values.append('')

        csv_writer.write(values)

    csv_writer.write(
        ['Average Override', 'Average Default', 'Average Difference'])

    csv_writer.write(grader.get_averages(groups, course))

    return csv_writer.get_response()


def assessments_csv(course):
    """Creates csv response for course assessments"""

    csv_writer = CSVWriter('Assessments', course)

    assessments = [
        assessment for assessment in course.assessment_set.all()]
    header = ('Assessment', 'Default', 'Minimum', 'Maximum')

    csv_writer.write(header)

    for assessment in assessments:
        values = (assessment.title, assessment.default,
                  assessment.min, assessment.max)
        csv_writer.write(values)

    return csv_writer.get_response()
