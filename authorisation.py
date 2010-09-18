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
Module containing classes and utility functions related to AmCAT authorisation

Main entry points are

getPrivilege(db, str or int) returns Privilege object
check(db, privilege/str/int) checks whether user has privilege
"""

def check(db, privilege):
    """Check whether the logged-in user is authorised for the privilege

    If permission is denied, will raise L{AccessDenied}; otherwise will
    return silently
    
    @param db: db connection with the 'current user' logged in
    @type privilege: Privilege object, id, or str
    @param privilege: The requested privilege
    @return: None (raises exception if denied)
    """
    pass
