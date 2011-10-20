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


from amcat.scripts import script
from amcat.scripts import cli
import amcat.scripts.forms
#from amcat.scripts.searchscripts.articleids import ArticleidsScript
from django import forms
import itertools
import xml.sax.saxutils
import tempfile, os, subprocess, re

import logging
log = logging.getLogger(__name__)


class ClustermapScript(script.Script):
    input_type = script.ArticleidDictPerQuery
    options_form = None
    output_type = script.ImageMap


    def run(self, articleidDict):
        allArticleids = set(itertools.chain(*articleidDict.values()))
        
        objects = []
        for id in allArticleids:
            objects.append("""
            <Object ID="%(id)s">
             <Name>Click to View Article</Name>
             <Location>%(id)s</Location>
            </Object>""" % {'id':id})
        objects = '\n'.join(objects)

        classifications = []
        for keyword, articleids in articleidDict.items():
            keywordStr = xml.sax.saxutils.escape(keyword)
            keywordQuote = xml.sax.saxutils.quoteattr(keyword)
            articleidStr = ' '.join(map(str, articleids))
            classifications.append("""
            <Classification ID=%s>
             <Name>%s</Name>
             <SuperClass refs="root" />
             <Objects objectIDs="%s" />
            </Classification>""" % (keywordQuote, keywordStr, articleidStr))
        classifications = '\n'.join(classifications)
        
        allArticleidStr = ' '.join(map(str, allArticleids))
        clusterXml = u"""<?xml version="1.0" encoding="utf-8"?>
        <ClassificationTree version="1.0">
          <ObjectSet>%s</ObjectSet>
          <ClassificationSet>
            <Classification ID="root">
                <Name>Root</Name><Objects objectIDs="%s" />
            </Classification>
            %s
          </ClassificationSet>
        </ClassificationTree>
        """ % (objects, allArticleidStr, classifications)
        
        imgfiledesc, imgfilepath = tempfile.mkstemp()
        os.close(imgfiledesc)
        
        xmlfiledesc, xmlfilepath = tempfile.mkstemp()
        os.write(xmlfiledesc, clusterXml)
        os.close(xmlfiledesc)
        
        log.info('temp files: %s and %s' % (imgfilepath, xmlfilepath))
        
        cmd = """ \
        java -Xmx800M \
        -classpath /home/amcat/lib/java:/home/amcat/resources/jars/aduna-clustermap-2006.1.jar:/home/amcat/resources/jars/aduna-clustermap-2006.1-resources.jar \
        Cluster "%s" "%s"
        """ % (xmlfilepath, imgfilepath)

        #mapHtml, errorMessage = toolkit.execute(cmd)
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        mapHtml, err = proc.communicate()
        if mapHtml == '':
            raise Exception('Clustermap error: %s' % err)
        
        log.info(mapHtml[:1000])

        mapHtml = re.sub('<AREA', '<AREA onclick="return false"', mapHtml)
        mapHtml = re.sub('onMouseOut="JavaScript:clearAll\(\);"', '', mapHtml)
        mapHtml = re.sub('onMouseOver="JavaScript:setTitleAndUrl\(.*?\);"', '', mapHtml)
        
        articleCount = len(allArticleids)
        
        image = open(imgfilepath).read()
        
        os.remove(xmlfilepath)
        os.remove(imgfilepath)
        
        return script.ImageMap(mapHtml, image, articleCount)
        
        
        
        
if __name__ == '__main__':
    cli.run_cli(ClustermapScript)