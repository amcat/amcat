from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from amcat.tools import amcates

class FlushView(APIView):
    def get(self, request):
        amcates.ES().flush()
        return Response({"flushed": True}, status=HTTP_200_OK)
