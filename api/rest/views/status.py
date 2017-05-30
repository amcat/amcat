import time
import os

from celery.exceptions import TimeoutError
from git import InvalidGitRepositoryError, Repo
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView

import amcat
from amcat.amcatcelery import status
from amcat.tools.amcates import ES


class StatusView(APIView):
    def get(self, request):
        data = {"amcat": status(),
                'elastic': ES().status(),
                'git': git_status()}
        try:
            data['celery_worker'] = status.delay().wait(timeout=3)
        except TimeoutError:
            data['celery_worker'] = {"Error": "Timeout on getting worker status"}
        data['celery_queues'] = queue_status()
        
        return Response(data, status=HTTP_200_OK)


def queue_status():
    from amqplib import client_0_8 as amqp
    from amcat.amcatcelery import app
    result = {}

    def _inspect_queue(queue, **conn_kwargs):
        conn = amqp.Connection(insist=False, virtual_host="/", **conn_kwargs)
        name, ntask, nconsumer = conn.channel().queue_declare(queue=queue, passive=True)
        return {"queue": name, "#tasks": ntask, "#consumer": nconsumer}
    
    #amcat queue  - should read config instead of assuming localhost?
    amcatq = app.conf['CELERY_DEFAULT_QUEUE']
    result["amcat"] = _inspect_queue(amcatq, host="localhost:5672", userid="guest", password="guest")

    return result

def git_status():
    def date2iso(date):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(date))
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
            "committed_date": date2iso(repo.head.commit.committed_date),
            "commtter": str(repo.head.commit.committer)}}
        
