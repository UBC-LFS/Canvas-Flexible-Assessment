import numbers
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from .models import Assessment


class AddAssessmentForm(ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        default = cleaned_data.get('default')
        min = cleaned_data.get('min')
        max = cleaned_data.get('max')

        allocations = [('Default', default), ('Maximum', max), ('Minimum', min)]
        validation_errors = []

        for name, allocation in allocations:
            if allocation and (allocation > 100.0 or allocation < 0.0):
                validation_errors.append(ValidationError('{} must be within 0.0 and 100.0'.format(name)))

        if default and min and max:
            if min > default:
                validation_errors.append(ValidationError('Minimum must be lower than default'))
            if default > max:
                validation_errors.append(ValidationError('Maximum must be higher than default'))
            if min > max:
                validation_errors.append(ValidationError('Maximum must be higher than minimum'))

        if validation_errors:
            raise ValidationError(validation_errors)


    class Meta:
        model = Assessment
        fields = ['title', 'default', 'min', 'max']
        help_texts = {'title': 'Enter assessment title',
                      'default': 'Default grade allocation',
                      'min': 'Minimum possible grade allocation set by student',
                      'max': 'Maximum possible grade allocation set by student'}
