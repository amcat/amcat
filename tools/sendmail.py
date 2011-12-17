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

"""Module for creating an email message and sending it using /usr/sbin/sendmail"""

from __future__ import unicode_literals, print_function, absolute_import

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from amcat.tools import toolkit


SENDMAIL = "/usr/sbin/sendmail"

def _create_message(sender, recipient, subject, html, plain):
    """Create a mime multipart message ready for sending"""
    # thanks to http://code.activestate.com/recipes/473810/ 
    msgRoot = MIMEMultipart('related')
    msgRoot['Subject'] = subject
    msgRoot['From'] = sender
    msgRoot['To'] = recipient
    msgRoot.preamble = 'This is a multi-part message in MIME format.'

    # Encapsulate the plain and HTML versions of the message body in an
    # 'alternative' part, so message agents can decide which they want to display.
    msgAlternative = MIMEMultipart('alternative')
    msgRoot.attach(msgAlternative)

    msgAlternative.attach(MIMEText(plain))

    msgAlternative.attach(MIMEText(html, 'html'))
    
    return msgRoot.as_string()

def sendmail(sender, recipient, subject, html, plain):
    """Send an email from sender to recipient using the unix sendmail command"""
    mail = _create_message(sender, recipient, subject, html, plain)
    cmd = "%s -t" % SENDMAIL
    out = toolkit.execute(cmd, mail, outOnly=True)
    if out.strip(): raise Exception(out)
    
if __name__ == '__main__':
    # actual test in __name__ to prevent getting an email everytime the tests run
    sendmail("wouter@vanatteveldt.com", "vanatteveldt@gmail.com", "Test mailtje",
             "bla <b>nla!</b>", "bla bla")
        


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestSendMail(amcattest.PolicyTestCase):

    def test_create_message(self):
        """Can we create a message?"""
        msg = _create_message("wouter@vanatteveldt.com", "vanatteveldt@gmail.com",
                              "Test mailtje", "bla <b>nla!</b>", "bla bla")
        self.assertIn("\nFrom: wouter@vanatteveldt.com\n", msg)
        self.assertIn("\nTo: vanatteveldt@gmail.com\n", msg)
        self.assertIn('Content-Type: text/html; charset="us-ascii"'
                      '\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\n'
                      'bla <b>nla!</b>\n', msg)

        
     
