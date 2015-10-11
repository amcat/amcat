from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from amcat.amcatcelery import status
from amcat.tools.amcates import ES
from git import Repo
import time

class StatusView(APIView):
    def get(self, request):
        data = {"amcat": status(),
                'celery_worker': status.delay().wait(),
                'elastic': ES().status(),
                'git': git_status()}
        return Response(data, status=HTTP_200_OK)


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
        
