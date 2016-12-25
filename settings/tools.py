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
import configparser
import functools
import os
import sys

import amcat
from amcat.tools.toolkit import random_alphanum


@functools.lru_cache()
def get_amcat_config() -> configparser.ConfigParser:
    """
    Reads configuration files in this order:

     * /etc/default/amcat
     * /etc/amcat.ini
     * ~/.amcat.ini
    """
    default_ini = os.path.join(amcat.__file__, "../../settings/amcat.ini")
    config = configparser.ConfigParser()
    config.read(os.path.abspath(default_ini))
    config.read("/etc/default/amcat", "utf-8")
    config.read("/etc/amcat/amcat.ini", "utf-8")
    config.read(os.path.expanduser("~/.amcat.ini"), "utf-8")

    if os.environ.get("AMCAT_CONFIG", "").strip():
        if not config.read(os.environ["AMCAT_CONFIG"]):
            raise OSError("Could not read: {}".format(os.environ["AMCAT_CONFIG"]))

    if "runserver" in sys.argv:
        config["base"]["debug"] = True

    return config


def get_cookie_secret():
    """
    Get or create a secret key to sign cookies with.

    ~/.cookie-secret will be used to store the secret key.
    """
    sfile = os.path.expanduser("~/.cookie-secret")

    if os.path.exists(sfile):
        if os.path.isfile(sfile):
            try:
                with open(sfile) as f:
                    return f.read()
            except IOError:
                print("%r is not readable!" % sfile)
                raise
        else:
            print("%r is not a file." % sfile)
            raise ValueError("%r is not a file." % sfile)

    with open(sfile, 'w') as sfile:
        sfile.write(random_alphanum(40))

    return get_cookie_secret()