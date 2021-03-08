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
from rpy2.rinterface_lib.embedded import RRuntimeError

from amcat.scripts.query import get_r_queryactions
from amcat.scripts.query.queryaction_r import R_DEPENDENCIES




class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--update', '-U', action='store_true')


    def handle(self, *args, **options):
        from rpy2.robjects import r
        def get_installed_version(package):
            try:
                return r("as.character")(r.packageVersion(package))[0]
            except RRuntimeError as e:
                return None
        available_packages = r("available.packages()[,'Version']")
        available_packages = dict(zip(r.names(available_packages), available_packages))

        for package in ["rjson", "remotes"]:
            available = available_packages.get(package)
            installed = get_installed_version(package)
            if (not installed) or (options['update'] and installed != available):
                print(f"Installing {package} (required before reading dependencies)")
                r("install.packages")(package)

        packages = {(name or dep): dep for (name, dep) in R_DEPENDENCIES.items()}
        for qa in get_r_queryactions():
            for name, dep in qa.get_dependencies().items():
                packages[name or dep] = dep

        def printrow(package, installed, available, src=None):
            print("{package:30s}{installed:10s}{available:10s} {}".format(src or "", **locals()))
        printrow("Package", "Installed", "Available", '(source)')

        todo = {}
        for package, src in packages.items():
            installed = get_installed_version(package)
            available = "?" if "/" in src else available_packages.get(package)

            if not installed:
                installed = '-'
                todo[package] = src
            elif options['update'] and installed != available:
                todo[package] = src
            printrow(package, installed, available, src if src != package else None)
        print("\nInstalling required packages: ", todo)
        for package in [pkg for (pkg, src) in todo.items() if "/" not in src]:
            print("... ", package)
            r("install.packages")(package)
        for package, src in todo.items():
            if "/" in src:
                print("... ", package, " <- ", src)
                r("remotes::install_github")(src, upgrade='always')
        print("\nDone!")


