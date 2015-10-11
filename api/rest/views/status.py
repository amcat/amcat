from rest_framework.views import APIView
from rest_framework import generics
from rest_framework import serializers
from rest_framework.response import Response

from amcat.amcatcelery import status

class BaseStatusSerializer(serializers.Serializer):
    amcat_version = serializers.CharField()
    hostname = serializers.CharField()
    folder = serializers.CharField()
    default_celery_queue = serializers.CharField()
    
class CeleryStatusSerializer(BaseStatusSerializer):
    task_id = serializers.CharField()
    exchange = serializers.CharField()
    routing_key = serializers.CharField()
    
    
class StatusSerializer(BaseStatusSerializer):
    celery_worker = CeleryStatusSerializer(many=False)
    

class StatusView(generics.GenericAPIView):
    serializer_class = StatusSerializer
    
    def get(self, request):
        data = status()
        data['celery_worker'] = status.delay().wait()
        serializer = self.get_serializer(data)
        return Response(serializer.data)
