import json
from webscript import WebScript
from amcat.scripts.searchscripts.articlelist import ArticleListScript
from amcat.scripts.forms import SelectionForm
from amcat.tools import keywordsearch

import logging

stats_log = logging.getLogger("statistics:" + __name__)


class ShowSummary(WebScript):
    name = "Summary"
    form_template = None
    form = None
    
    def run(self):
        self.progress_monitor.update(1, "Creating summary")

        if isinstance(self.data['projects'], (basestring, int)):
            project_id = int(self.data['projects'])
        else:
            project_id = int(self.data['projects'][0])

        sf = SelectionForm(self.project, self.data)
        sf.full_clean()
        n = keywordsearch.get_total_n(sf.cleaned_data)
        self.progress_monitor.update(39, "Found {n} articles in total".format(**locals()))
        articles = list(ArticleListScript(self.data).run())
        for a in articles:
            a.hack_project_id = project_id
        self.output_template = 'api/webscripts/articlelist.html'
        self.progress_monitor.update(40, "Created summary")

        stats_log.info(json.dumps({
            "action": "query:summary", "user": self.user.username,
            "project_id": self.project.id, "project_name": self.project.name
        }))
            
        return self.outputResponse(dict(articlelist=articles, n=n, page=self.data.get('start')), ArticleListScript.output_type)
