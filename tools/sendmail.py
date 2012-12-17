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

"""
Module for creating an email message and sending it using django
Can probably be refactored away since it is so trivial now?
"""

from __future__ import unicode_literals, print_function, absolute_import

from django.core.mail import EmailMultiAlternatives

def sendmail(sender, recipient, subject, html, plain):
    msg = EmailMultiAlternatives(subject, plain, sender, [recipient])
    if html:
        msg.attach_alternative(html, "text/html")
    msg.send()
    
if __name__ == '__main__':
    # actual test in __name__ to prevent getting an email everytime the tests run
    sendmail("amcat.vu@gmail.com", "vanatteveldt@gmail.com", "Test mailtje 2345",
             "bla <b>nla!</b>", "bla bla")
        
