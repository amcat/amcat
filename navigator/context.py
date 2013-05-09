from amcat.models import AmCAT

# Extra context variables
def extra(request):
    return dict(request=request, announcement=AmCAT.get_instance().get_announcement())
