#!/usr/bin/python
##########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################


import logging; log = logging.getLogger(__name__)

import json

from django import forms

from amcat.scripts.script import Script
from amcat.models import CodingJob
from amcat.models.coding.serialiser import _CodebookSerialiser
from amcat.tools.amcates import ES

class IndexCodings(Script):
    """
    Copy the (article) codings of a specified job to elastic
    """

    class options_form(forms.Form):
        job = forms.ModelChoiceField(queryset=CodingJob.objects.all())


    def _run(self, job):
        es = ES()
        for ca in job.coded_articles.all():
            coding_json = {"job": job.id, "sentence_codings": []} 
            
            for coding in ca.codings.all():
                values = {}
                print((coding, coding.sentence))
                for cv in coding.values.all():
                    fieldtype = cv.field.fieldtype.name
                    if fieldtype == "Codebook":
                        values[cv.field.label] = cv.intval
                        values[cv.field.label + "_label"] = cv.value.label
                    elif fieldtype == "Text":
                        values[cv.field.label + "_label"] = cv.value
                    elif fieldtype == "Quality":
                        values[cv.field.label] = cv.value / 10
                    elif fieldtype == "Yes/No":
                        values[cv.field.label + "_bool"] = cv.value
                    else:
                        values[cv.field.label] = cv.value
                
                if coding.sentence_id is None:
                    coding_json["article_coding"] = values
                else:
                    values["sentence_id"] = coding.sentence_id
                    coding_json["sentence_codings"].append(coding)

            src = es.get(ca.article_id)
            src["codings"] = [c for c in src.get('codings', [])
                              if not c['job'] == job.id]
            src['codings'].append(coding_json)
            es.es.index(index=es.index, doc_type=es.doc_type, id=ca.article_id, body=src)
            #print(json.dumps(src, indent=2))


if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()

    # cli doesn't work atm
    import django
    django.setup()
    import sys
    IndexCodings({'job': int(sys.argv[1])}).run()
