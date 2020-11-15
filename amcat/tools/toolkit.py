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
Toolkit of useful methods for AmCAT

Policy:
 - Each public function should be documented!
 - It should pass pychecker without warnings
 - We should try to make good test cases in test/test_toolkit.py

This toolkit is divided into a number of sections, please stick to
this organisation!
 - decorators
 - sequence functions
 - mapping functions
 - string functions
 - date(time) functions
 - misc functions
"""

import collections
import datetime
import itertools
import logging
import random
import string
import time
from typing import Sequence

import amcat.tools.dateparsing

log = logging.getLogger(__name__)


###########################################################################
##                            Decorators                                 ##
###########################################################################
def synchronized_with(lock):
    def decorator(func):
        def synced_func(*args, **kws):
            with lock:
                return func(*args, **kws)

        return synced_func

    return decorator


###########################################################################
##                     Sequence functions                                ##
###########################################################################
def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks."""
    if n < 1:
        raise ValueError("Size of {} invalid for grouper() / splitlist().".format(n))
    return itertools.zip_longest(fillvalue=fillvalue, *([iter(iterable)] * n))


def splitlist(iterable, itemsperbatch=100):
    """Split a list into smaller lists. Uses no fillvalue, as opposed to grouper()."""
    _fillvalue = object()
    for group in grouper(iterable, itemsperbatch, _fillvalue):
        yield [e for e in group if e is not _fillvalue]


###########################################################################
##                      Mapping functions                                ##
###########################################################################

class multidict(collections.defaultdict):
    """A dictionary of key : set pairs"""

    def __init__(self, seq, ltype=set):
        """Create a new multidict from a seq of key,value pairs (with duplicate keys).

        @type seq: iterable

        @type ltype: set, list
        @param ltype: default dict key-value"""
        collections.defaultdict.__init__(self, ltype)

        add = self.add if ltype is set else self.append
        if seq:
            for kv in seq:
                if kv:
                    add(*kv)

    def add(self, key, value):
        self[key].add(value)

    def append(self, key, value):
        self[key].append(value)


###########################################################################
##                         String functions                              ##
###########################################################################

ACCENTS_MAP = {'a': '\xe0\xe1\xe2\xe3\xe4\xe5',
               'c': '\xe7',
               'e': '\xe9\xe8\xea\xeb',
               'i': '\xec\xed\xee\xef',
               'n': '\xf1',
               'o': '\xf3\xf2\xf4\xf6\xf8',
               'u': '\xf9\xfa\xfb\xfc',
               'y': '\xfd\xff',

               'A': '\xc0\xc1\xc2\xc3\xc4\xc5',
               'C': '\xc7',
               'E': '\xc8\xc9\xca\xcb',
               'I': '\xcc\xcd\xce\xcf',
               'N': '\xd1',
               'O': '\xd2\xd3\xd4\xd5\xd6\xd8',
               'U': '\xd9\xda\xdb\xdc',
               'Y': '\xdd',

               's': '\u0161\u015f',
               'ss': '\xdf',
               'ae': '\xe6',
               'AE': '\xc6',

               '?': '\xbf',
               "'": '\x91\x92\x82\u2018\u2019\u201a\u201b\xab\xbb\xb0',
               '"': '\x93\x94\x84\u201c\u201d\u201e\u201f\xa8',
               '-': '\x96\x97\u2010\u2011\u2012\u2013\u2014\u2015',
               '|': '\xa6',
               '...': '\x85\u2026\u2025',
               '.': '\u2024',
               ' ': '\x0c\xa0',
               '\n': '\r',
               "2": '\xb2',
               "3": '\xb3',
               # u"(c)" : u'\xa9',
               }


_REV_ACCENTS_MAP = None
def _get_accents_map():
    global _REV_ACCENTS_MAP
    if _REV_ACCENTS_MAP is None:
        _REV_ACCENTS_MAP = {}
        for to, from_characters in ACCENTS_MAP.items():
            for from_character in from_characters:
                if from_character in _REV_ACCENTS_MAP:
                    raise ValueError("Character {} occured twice on right-hand side".format(from_character))
                _REV_ACCENTS_MAP[from_character] = to
    return _REV_ACCENTS_MAP


def strip_accents(s):
    """Replace accented characters in s by their unaccepted equivalents

    @param s: the string to strip accents from.
    @return: a str string containing the translated input
    """
    # [WvA] this can probably be replaced by unidecode?
    return "".join(_get_accents_map().get(c, c) for c in s)


###########################################################################
##                     Date(time) functions                              ##
###########################################################################

# retain read_date reference for backwards compatibility
read_date = amcat.tools.dateparsing.read_date

def to_datetime(date):
    """Convert datetime.date object to datetime.datetime or truncate datetime.datetime to a whole day"""
    return datetime.datetime(year=date.year, month=date.month, day=date.day)


###########################################################################
##                         Misc. functions                               ##
###########################################################################
# Please try to keep this one clean...

class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.interval = self.end - self.start


def random_alphanum(size=10):
    # TODO: Should switch to secrets ASAP (https://docs.python.org/3.5/library/secrets.html)
    def crypto_choice(rng: random.SystemRandom, choices: Sequence):
        return choices[rng.randrange(0, len(choices))]

    cryptogen = random.SystemRandom()
    choices = string.ascii_letters + string.digits
    return ''.join([crypto_choice(cryptogen, choices) for i in range(size)])
