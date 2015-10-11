from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from amcat.amcatcelery import status
from amcat.tools.amcates import ES

class StatusView(APIView):
    def get(self, request):
        data = status()
        data['celery_worker'] = status.delay().wait()
        data['elastic'] = ES().status()
        return Response(data, status=HTTP_200_OK)

