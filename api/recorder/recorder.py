from django.http import HttpResponse, HttpResponseBadRequest
from amcat.models.record import Record
from amcat.models.article import Article
from amcat.models.coding.codingjob import CodingJob
import dateutil.parser
import json

def record(request):
    record_list = json.loads(request.body)
    for record_entry in record_list:
        record_entry['user'] = request.user
        record_entry['ts'] = dateutil.parser.parse(record_entry['ts'])
        if 'article_id' in record_entry:
            article = Article.objects.get(id=record_entry['article_id'])
            record_entry['article'] = article
            del record_entry['article_id']
        if 'codingjob_id' in record_entry:
            codingjob = CodingJob.objects.get(id=record_entry['codingjob_id'])
            record_entry['codingjob'] = codingjob
            del record_entry['codingjob_id']
        Record.objects.create(**record_entry)            
    return HttpResponse(json.dumps({}), content_type='application/json')


