from .models import Course


def add_course_to_context(request):
    """Adds course object reference to context

    Parameters
    ----------
        request : request
            Contains request data
    """

    context_addition = {}
    if request.session.get('course_id', ''):
        context_addition['course'] = Course.objects.get(
            pk=request.session['course_id'])
    if request.session.get('display_name', ''):
        context_addition['display_name'] = request.session['display_name']

    return context_addition
