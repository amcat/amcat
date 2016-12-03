# ##########################################################################
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

"""
Plugin for uploading .eml (outlook & others) files of a certain markup, provided by BZK
"""

import re
import logging
from datetime import timedelta

from amcat.scripts.article_upload.upload import UploadScript
from amcat.tools.toolkit import read_date
from amcat.models.article import Article
from amcat.scripts.article_upload.bzk_aliases import BZK_ALIASES


log = logging.getLogger(__name__)


class BZKEML(UploadScript):
    def _scrape_unit(self, _file):
        readlines = _file.readlines()
        file_date_line = [l for l in readlines if l.startswith("Date:")][0]
        file_date = read_date(file_date_line.split("Date:")[1])

        lines = []
        mail_header = []
        for line in readlines:
            if lines:
                lines.append(line.rstrip("\r\n"))
            else:
                mail_header.append(line)
            if line.startswith("1red"):  #actual content starts
                lines.append("")

        article = Article(metastring={'mail_header': "".join(mail_header)})

        while True:  #loop through lines up to and including headline
            line = lines.pop(0)
            if line.isupper():
                article.title = line
                break
            elif line:  #first non-empty line, contains metadata
                data = line.split(", ")
                datestr = data[0]
                if "'" in datestr:
                    split = datestr.split("'")
                    datestr = split[0] + "20" + split[1]
                if "=" in datestr:  # if this is true, the year is not parsable
                    # we take the year the mail was sent, might fail around december
                    datestr = datestr.split("=")[0] + str(file_date.year)
                    article.date = read_date(datestr)
                    if (
                                article.date - file_date).days > 200:  #likely a misparse, with the mail being sent the next year
                        article.date -= timedelta(years=1)
                else:
                    article.date = read_date(datestr)
                if data[2] in BZK_ALIASES.keys():
                    medium_str = BZK_ALIASES[data[1]]
                else:
                    medium_str = data[2]
                article.set_property("medium", medium_str)
                article.set_property("section", data[1])

        paragraphs = []
        paragraph = ""
        while True:
            line = lines.pop(0).rstrip("=")
            if not line:
                paragraphs.append(paragraph)
                paragraph = ""
            elif line.isupper():  #subheader
                paragraph += line + "\n"
            else:
                paragraph += line
            if not lines:
                break
        paragraphs = [p for p in paragraphs if p]

        article.text = ""
        for p in paragraphs:
            article.text += p + "\n\n"
            if p.startswith("(") and len(p.split(",")) > 1:  #laatste regel van normale content
                break

        # Add non-ascii characters
        # Takes the '=AB' occurrences and turns them into latin-1 characters.
        def character(match):
            code = match.group()[1:]
            char = r"\x{}".format(code).decode('string-escape').decode('latin-1')
            if code == "92":
                return "'"
            elif code == "85":
                return "..."
            return char

        article.text = re.sub(
            "=[A-Z0-9]{2}",
            character,
            article.text)

        yield article


if __name__ == "__main__":
    from amcat.scripts.tools import cli

    cli.run_cli(BZKEML)


