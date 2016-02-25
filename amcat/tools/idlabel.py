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
Auxilliary classes to aid making comparable classes based on any identity (L{Identity})
or specifically on an integral id with an associated label (L{IDLabel})
"""

import logging;

log = logging.getLogger(__name__)


class Identity(object):
    """
    Simple class representing an object which can be compared to
    other Identity objects based on an identity() function
    """
    __slots__ = '__identity__'

    def __init__(self, *identity):
        self.__identity__ = tuple([self.__class__] + list(identity)) if identity else None

    def _identity(self):
        if self.__identity__:
            return self.__identity__
        raise Exception("Identity object without identity")

    def __eq__(self, other):
        if other is None: return False
        try:
            return self._identity() == other._identity()
        except AttributeError:
            return False


class IDLabel(Identity):
    """
    Simple class representing objects with a label and ID. Identity checks equality
    on class + ID; str( ) returns the label, repr( ) return class(id, label, ..)
    """
    #__slots__ = ('id', '_label')
    def __init__(self, id, label=None):
        Identity.__init__(self, self.__class__, id)
        self.id = id
        self._label = label

    @property
    def label(self):
        if self._label is None:
            log.warn("%r has no label" % self)
            return repr(self)
        return self._label

    def identity(self):
        return (self.__class__, self.id)

    def clsidlabel(self):
        return "%s %s" % (type(self).__name__, self.idlabel())

    def idlabel(self):
        return "%s: %s" % (self.id, str(self))

    def __bytes__(self):
        return bytes(self.label)

    def __str__(self):
        return str(self.label)

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.id)

    def __hash__(self):
        return hash(self.id)
