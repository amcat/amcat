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
import logging;

from django.core.management import BaseCommand, CommandError

from amcat.models import AmCAT
from amcat.scripts.actions.cache_articleset_mediums import CacheArticleSetMediums


log = logging.getLogger(__name__)

ERR = "You should pass an action: on, off or warm."

class Command(BaseCommand):
    args = '[on|off|warm]'
    help = 'Enables / disables / warms medium caching (see articleset.py). Warm call on when done.'

    def handle(self, *args, **options):
        if not len(args) or args[0] not in ("on", "off", "warm"):
            raise CommandError(ERR)

        if args[0] == "on":
            log.info("Enabling medium caching..")
            enable = True

        if args[0] == "off":
            log.info("Disabling medium caching..")
            enable = False

        if args[0] in ("on", "off"):
            AmCAT.enable_mediums_cache(enable)
            log.info("OK.")

        if args[0] == "warm":
            CacheArticleSetMediums().run()
            self.handle("on")
