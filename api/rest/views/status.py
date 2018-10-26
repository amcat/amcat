import datetime
import functools
import os
import time
from collections import OrderedDict

from git import InvalidGitRepositoryError, Repo
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView

import amcat
from amcat.amcatcelery import status
from amcat.tools.amcates import ES
from settings import amcat_config

class StatusView(APIView):
    def get(self, request):
        data = OrderedDict()
        data['amcat'] = amcat_status()
        data['elastic'] = es_status()
        data['git'] = git_status()
        data['celery_worker'] = worker_status()
        data['celery_queues'] = queue_status()

        return Response(data, status=HTTP_200_OK)

def _nofail(func):
    """
    Catches all exceptions thrown by func, and returns a serializable error message.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {type(e).__name__: str(e)}
    return wrapper


@_nofail
def amcat_status():
    return status()

@_nofail
def es_status():
    return ES().status()

@_nofail
def worker_status():
    return status.delay().wait(timeout=3)

@_nofail
def queue_status():
    from amqplib import client_0_8 as amqp
    result = {}

    def _inspect_queue(queue, **conn_kwargs):
        conn = amqp.Connection(insist=False, virtual_host="/", **conn_kwargs)
        name, ntask, nconsumer = conn.channel().queue_declare(queue=queue, passive=True)
        return {"queue": name, "#tasks": ntask, "#consumer": nconsumer}
    
    celery_config = amcat_config['celery']
    host = "{amqp_host}:{amqp_port}".format(**celery_config)
    try:
        result["amcat"] = _inspect_queue(celery_config['queue'], host=host, userid=celery_config['amqp_user'],
                                         password=celery_config['amqp_passwd'])
    except UnboundLocalError:
        # UnboundLocalError is thrown due to a bug in the error handling in the amqp library.
        raise ConnectionRefusedError("Host '{}' refused the connection.".format(host))

    return result

@_nofail
def git_status():
    def isodate(commit):
        tz = datetime.timezone(-datetime.timedelta(seconds=commit.committer_tz_offset))
        date = datetime.datetime.fromtimestamp(commit.committed_date, tz=tz)
        return date.isoformat()
    # there is probably a better place for this!
    try:
        amcat_dir = os.path.dirname(amcat.__path__[0])
        repo = Repo(amcat_dir)
    except InvalidGitRepositoryError:
        return None #Not a git repo

    return {
        "active_branch": str(repo.active_branch),
        "last_commit": {
            "summary": repo.head.commit.summary,
            "committed_date": isodate(repo.head.commit),
            "commtter": str(repo.head.commit.committer),
            "sha": repo.head.commit.hexsha[:7],
        }
    }