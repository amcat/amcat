##########################################################################
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
import glob
import inspect
import os

from amcat.scripts.query.queryaction_r import RQueryAction


__all__ = {"get_r_queryactions"}


def create_action(path: str):
    """Based on a path pointing to an R-script, create an RQueryAction and register
    it as a global variable in this module."""
    filename = os.path.basename(path)
    classname = "".join(p.title() for p in filename[:-2].split("_")) + "Action"
    raction = type(classname, (RQueryAction,), {
        "output_types": (("text/html", "Result"),),
        "r_file": path
    })

    globals()[classname] = raction
    __all__.add(classname)


def get_r_queryactions():
    for cls in map(globals().get, __all__):
        if inspect.isclass(cls) and issubclass(cls, RQueryAction):
            yield cls


# Get local plugins
system_dir = os.path.join(os.path.dirname(__file__), "r_plugins")
for path in glob.glob(os.path.join(system_dir, "*.r")):
    if path.endswith("/formfield_functions.r"):
        continue
    create_action(path)

# Get plugins from user directories
user_dir = os.path.expanduser("~/amcat_plugins/r")
for path in glob.glob(os.path.join(user_dir, "*.r")):
    create_action(path)

__all__ = list(__all__)

