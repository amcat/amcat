#!/usr/bin/python
###########################################################################
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

import logging
log = logging.getLogger(__name__)

from django.db import transaction
from django import forms

from amcat.models import CodingJob, Coding
from amcat.scripts.script import Script

class AutocodeScript(Script):

    class options_form(forms.Form):
        job = forms.ModelChoiceField(queryset=CodingJob.objects.all())
        fieldname = forms.CharField()

    def run(self, _input = None):
        job = self.options["job"]
        field = job.unitschema.fields.get(label = self.options["fieldname"])
        codes = list(field.codebook.codes)
        add_codings(job, field, codes)

        
def add_coding(job, sent, field, code):
    # Check if coding exists
    #if Coding.objects.filter(codingjob=job, article=sent.article, sentence=sent).exists():
    #    raise Exception("Coding already exists!")
    # create Coding object
    coding = Coding.objects.create(codingjob=job, article=sent.article, sentence=sent)
    # set value
    coding.set_value(field, code)

    log.info("  Created coding %r: %r" % (coding, code))

ADHOC = {'telegraaf.nl' : 'Telegraaf',
         'trouw.nl' : 'Trouw',
         'volkskrant.nl' : 'Volkskrant',
         'ad.nl' : 'AD',
         'fd.nl': 'Financieele Dagblad',
         'nrc.nl' : 'NRC',
         'Algemeen Dagblad' : "AD",
         "Financieel Dagblad" : "Financieele Dagblad" ,
         "Financiele Dagblad" : "Financieele Dagblad" ,
}

def code_in_sent(sent, label):
    if label in sent:
        return True
    for adhoc, adhoc_label in ADHOC.iteritems():
        if label == adhoc_label and adhoc in sent:
            return True


@transaction.commit_on_success
def add_codings(job, field, codes):
    for a in job.articleset.articles.all().only("id").prefetch_related("sentences"):
        coded = False
        log.info("Coding article %r" % a.headline)
        if Coding.objects.filter(codingjob=job, article=a).exists():
            raise Exception("Coding already exists!")
        for s in a.sentences.all():
            for code in codes:
                if code_in_sent(s.sentence, code.label):
                    print job.id, s.id, s.sentence, code
                    add_coding(job, s, field, code)
                    coded = True


        coding = Coding.objects.create(codingjob=job, article=a)
        coding.set_status(1 if coded else 9)

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()


