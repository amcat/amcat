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
import random
import string
import types

from django.core.cache import cache
from hashlib import sha1

def gen_random(n=8):
    return ''.join(random.choice(string.ascii_uppercase) for x in range(n))

def cache_function(length):
    """
    Caches a function, using the function itself as the key, and the return
    value as the value saved. It passes all arguments on to the function, as
    it should.
    
    @type length: integer
    @param length: seconds to cache
    """
    def decorator(func):
        def inner_func(*args, **kwargs):
            keys = map(str, (func.__module__, func.__name__, args, kwargs))
            key = sha1("_".join(keys)).hexdigest()

            if cache.has_key(key):
                return cache.get(key)
            else:
                result = func(*args, **kwargs)

                if type(result) == types.GeneratorType:
                    result = tuple(result)

                cache.set(key, result, length)
                return result
        return inner_func
    return decorator
