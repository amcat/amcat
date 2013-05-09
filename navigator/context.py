from amcat.models import AmCAT

DISPLAY_COUNT = 3
ANNOUCE_KEY = "last_announcement"
COUNT_KEY = "last_announcement_count"

# Extra context variables
def extra(request):
    announcement = AmCAT.get_instance().get_announcement()
    last_announcement = request.session.get(ANNOUCE_KEY)
    count = int(request.session.get(COUNT_KEY, 0)) + 1

    if last_announcement == announcement and count >= DISPLAY_COUNT:
        announcement = None
    elif last_announcement != announcement:
        request.session["last_announcement"] = announcement
        count = 0

    if count < DISPLAY_COUNT:
        request.session[COUNT_KEY] = count

    return dict(request=request, announcement=announcement)
