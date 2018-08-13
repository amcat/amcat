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

from django.core.management import BaseCommand
from rpy2.rinterface._rinterface import RRuntimeError

from amcat.scripts.query import get_r_queryactions


class Command(BaseCommand):
    def handle(self, *args, **options):
        packages = set()
        for qa in get_r_queryactions():
            packages |= set(qa.get_dependencies())
        from rpy2.robjects import r

        available = r("available.packages()[,'Version']")
        available = dict(zip(r.names(available), available))

        printrow = lambda p, i, a: print("{:30s}{:10s}{:10s}".format(p, i, a))
        printrow("Package", "Installed", "Available")

        todo = []
        for package in packages:
            try:
                installed = r("as.character")(r.packageVersion(package))[0]
            except RRuntimeError as e:
                installed = '-'
                todo.append(package)
            printrow(package, installed, available.get(package))
        print("\nInstalling required packages: ", todo)
        for package in todo:
            print("... ", package)
            r("install.packages")(package)
        print("\nDone!")


