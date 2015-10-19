from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from celery.exceptions import TimeoutError

from amcat.amcatcelery import status
from amcat.tools.amcates import ES
from git import Repo
import time

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

    #xtas queues
    from xtas import celeryconfig as xc
    for queue in ["xtas", "corenlp", "background"]:
        result[queue] = _inspect_queue(queue, host="{}:5672".format(xc._BROKER_HOST),
                                       userid=xc._BROKER_USERNAME, password=xc._BROKER_PASSWORD)
    return result

def git_status():
    def date2iso(date):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(date))
    # there is probably a better place for this!
    repo = Repo()
    return {
        "active_branch": unicode(repo.active_branch),
        "last_commit": {
            "summary": repo.head.commit.summary,
            "committed_date": date2iso(repo.head.commit.committed_date),
            "commtter": unicode(repo.head.commit.committer)}}
        
