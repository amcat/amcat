# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, absolute_import
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

from amcat.scraping.document import Document, HTMLDocument
from amcat.scraping.scraper import HTTPScraper, DBScraper
from urllib import urlencode
from amcat.scraping import toolkit
import time
import json
import re
from datetime import datetime


INDEX_URL = "http://reader.google.com"
LOGIN_URL = "https://accounts.google.com/ServiceLoginAuth"
API_URL = "http://www.google.com/reader/api/0/stream/contents/feed/{feed_url}?r=n&c={continuation}&n=40&ck={timestamp}&client=scroll"






class GoogleReaderScraper(HTTPScraper, DBScraper):
    feedname = None

    def __init__(self, *args, **kwargs):
        if self.feedname == None:
            raise ValueError("please specify self.feedname, with exactly the same characters as in the HTML on the page")
        else:
            self.medium_name = self.feedname
        super(GoogleReaderScraper, self).__init__(*args, **kwargs)


    def _login(self, username, password):
        doc = self.getdoc(LOGIN_URL)
        form = toolkit.parse_form(doc)
        form['Email'] = username
        form['Passwd'] = password
        self.open(LOGIN_URL, urlencode(form))

    def get_feed_url(self, doc):
        js = doc.text_content()
        offset = js.find("_STREAM_LIST_SUBSCRIPTIONS")
        start = js.find("{", offset);end = js.find("]};", start)
        _json = js[start:end]
        for sub in _json.split("},{"):
            s = sub.find("title:") + 6
            title = sub[s:sub.find(",",s)].strip("\" ")
            if title == self.feedname:
                s = sub.find("id:") + 3
                return sub[s:sub.find(",",s)].strip('"').lstrip("fed/")


    def _get_units(self):
        index = self.getdoc(INDEX_URL) 
        
        feed_url = self.get_feed_url(index)
        if feed_url == None:
            raise ValueError("failed to obtain feed url, try adjusting self.feedname")
        timestamp = time.time()
        
        url = API_URL.format(continuation = "", **locals())
        while url != None:
            _json = self.open(url).read()
            data = json.loads(_json)
            continuation = data['continuation']
            for item in data['items']:
                _date = datetime.fromtimestamp(item['updated']).date()
                if _date == self.options['date']:
                    yield item
                elif _date < self.options['date']:
                    url = None;break
            if len(data['items']) < 40:
                url = None
            if url != None:
                timestamp = time.time()
                url = API_URL.format(**locals())

        
if __name__ == '__main__':
    print("this scraper is intended to be inherited from, please specify a feedname property when doing so")
    print()
    print("""has a _get_units method which returns (sample):
{
    "crawlTimeMsec" : "1359743077551",
    "timestampUsec" : "1359743077551808",
    "id" : "tag:google.com,2005:reader/item/e6e0c6ab2de81525",
    "categories" : [
        "user/13928480607847785759/state/com.google/reading-list",
        "user/13928480607847785759/state/com.google/fresh"],
    "title" : "CvdK Groningen wil miljard van NAM",
    "published" : 1359774129,
    "updated" : 1359774129,
    "alternate" : [
        {"href" : "http://feeds.nos.nl/~r/nosnieuws/~3/lxaxtIWAaaE/469381-cvdk-groningen-wil-miljard-van-nam.html","type":"text/html"}],
    "canonical" : [
        {"href":"http://nos.nl/tekst/469381-cvdk-groningen-wil-miljard-van-nam.html"}],
    "summary" : {
        "direction" : "ltr",
        "content" : "De Commissaris van de Koningin in Groningen, Max van den Berg, vindt dat de NAM minimaal 1 miljard euro moet steken in maatregelen om de gedupeerden van de aardgaswinning te compenseren. Dat geld staat los van de schadevergoeding van 100 miljoen die het kabinet toezegt.\u003cimg src\u003d\"http://feeds.feedburner.com/~r/nosnieuws/~4/lxaxtIWAaaE\" height\u003d\"1\" width\u003d\"1\"\u003e"},
    "likingUsers" : [],
    "comments" : [],
    "annotations" : [],
    "origin" : {
        "streamId" : "feed/http://feeds.nos.nl/nosnieuws",
        "title":"NOS.nl nieuws","htmlUrl":"http://nos.nl/"
    }
}""")


