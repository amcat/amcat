from django.http import HttpResponse, HttpResponseBadRequest
import json

def highlight(request, num="1"):
	article_id = request.GET.get('article_id')
	schema_id = request.GET.get('schema_id')
	if article_id is None or schema_id is None:
		 return HttpResponseBadRequest()
	return HttpResponse(json.dumps({}), content_type='application/json')