import csv

from django.http import Http404, HttpResponse
from django.utils import timezone

from . import grader


class CSVWriter:
    _writer = None
    _response = None

    def __init__(self, csv_title, course):
        self._response = HttpResponse(content_type='text/csv')
        self._response['Content-Disposition'] = 'attachment; filename=' \
            + '{}_{}_{}.csv'.format(csv_title,
                                    course.title.replace(' ', '-'),
                                    timezone.localtime()
                                    .strftime("%Y-%m-%dT%H%M"))

        self._writer = csv.writer(self._response, delimiter=",")

    def writerow(self, row):
        self._writer.writerow(row)

    def get_response(self):
        if not self._response:
            return Http404()
        return self._response


def students_csv(course, students):
    csv_writer = CSVWriter('Students', course)

    assessments = [
        assessment for assessment in course.assessment_set.all()]
    fields = ['Student'] + \
        [assessment.title for assessment in assessments] + ['Comment']

    csv_writer.writerow(fields)

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

        csv_writer.writerow(values)

    return csv_writer.get_response()


def grades_csv(course, students, groups):
    csv_writer = CSVWriter('Grades', course)

    assessments = [
        assessment for assessment in course.assessment_set.all()]

    titles = [
        "{} ({}%)".format(
            assessment.title,
            grader.get_group_weight(
                groups,
                assessment.group.id)) for assessment in assessments]

    fields = ['Student'] + titles + \
        ['Override Final Grade', 'Default Total', 'Difference']

    csv_writer.writerow(fields)

    for student in students:
        values = []
        values.append(
            '{}, {}'.format(
                student.display_name,
                student.login_id))

        for assessment in assessments:
            score = grader.get_score(groups, assessment.group.id, student)
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

        csv_writer.writerow(values)

    csv_writer.writerow(
        ['Average Override', 'Average Default', 'Average Difference'])

    csv_writer.writerow(grader.get_averages(groups, course))

    return csv_writer.get_response()


def assessments_csv(course):
    csv_writer = CSVWriter('Assessments', course)

    assessments = [
        assessment for assessment in course.assessment_set.all()]
    fields = ('Assessment', 'Default', 'Min', 'Max')

    csv_writer.writerow(fields)

    for assessment in assessments:
        values = (assessment.title, assessment.default,
                  assessment.min, assessment.max)
        csv_writer.writerow(values)

    return csv_writer.get_response()
