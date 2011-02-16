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
Auxilliary classes to aid making comparable classes based on any identity (L{Identity})
or specifically on an integral id with an associated label (L{IDLabel})
"""

from __future__ import unicode_literals, print_function, absolute_import
import logging; log = logging.getLogger(__name__)

class _Identity(object):
    __slots__ = ()
    def _identity(self):
	raise NotImplementedError()
    def __repr__(self):
        try:
            i = self._identity()
            if i[0] == self.__class__: i = i[1:]
            return "%s%r" % (type(self).__name__, i)
        except Exception, e:
            import traceback; traceback.print_exc()
            return "#ERROR on __repr__: %s" % e
    def __str__(self):
        return repr(self)
    def __hash__(self):
        return hash(self._identity())
    def __eq__(self, other):
        if other is None: return False
        if not isinstance(other, _Identity): return False
        return self._identity() == other._identity()
    def __cmp__(self, other):
        if not isinstance(other, _Identity): return -1
        return cmp(self._identity(), other._identity())



    
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
        return u"%s: %s" % (self.id, unicode(self))
    def __str__(self):
        try:
            if type(self.label) == unicode:
                return self.label.encode('ascii', 'replace')
            else:
                return str(self.label)
        except AttributeError:
            return repr(self)
    def __unicode__(self):
        try:
            if type(self.label) == unicode:
                return self.label
            else:
                return str(self.label).decode('latin-1')
        except AttributeError:
            return unicode(repr(self))
        
    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.id)
