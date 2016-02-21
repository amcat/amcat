
import logging

from amcat.models import Project

usage_log = logging.getLogger("amcat.usage")

def log_usage(username, type, action, project=None, **extra):
    if isinstance(project, Project):
        project = "{}: {}".format(project.id, project.name)
        
    extra.update({
        "username": username,
        "domain": type,
        "action": action,
        "project": project,
    })
    
    message = "{username}: {type} {action}".format(**locals())
    usage_log.info(message, extra=extra)

    
def log_request_usage(request, type, action, project=None, **extra):
    extra.update({
        "path": request.path,
        "remote_addr": request.META.get('REMOTE_ADDR'),
        "server_name": request.META.get('SERVER_NAME'),
    })
    log_usage(request.user.username, type, action, project, **extra)
    
