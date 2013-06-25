
import logging
log = logging.getLogger(__name__)
from amcat.models import AmCAT

DISPLAY_COUNT = 3
ANNOUNCE_KEY = "last_announcement"
COUNT_KEY = "last_announcement_count"

# Extra context variables
def extra(request):
    try:
        announcement = AmCAT.get_instance().global_announcement
    except:
        log.exception("Cannot get announcement")
        return dict(request=request)
    
    last_announcement = request.session.get(ANNOUNCE_KEY)
    count = int(request.session.get(COUNT_KEY, 0)) + 1

    if last_announcement == announcement and count >= DISPLAY_COUNT:
        announcement = None
    elif last_announcement != announcement:
        request.session["last_announcement"] = announcement
        count = 0

    if count < DISPLAY_COUNT:
        request.session[COUNT_KEY] = count

    return dict(request=request, warning=AmCAT.get_instance().server_warning, announcement=announcement)
