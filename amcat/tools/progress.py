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

import logging

from typing import Optional

log = logging.getLogger(__name__)

LOG_FORMAT = "[{name}{percent}%] {self.worked} / {self.total} {self.message!r}"

class ProgressMonitor(object):
    def __init__(self, total=100, message="In progress", name=None, log=True):
        self.total = total
        self.message = message
        self.worked = 0
        self.listeners = set()
        self.log = log
        self.name = name
        self.sub_monitors = set()
        self.progress = 0

    # Backwards compat.:
    @property
    def percent(self):
        return self.progress * 100

    def get_progress(self):
        my_progress = self.worked / self.total
        subprogress = sum(s.progress for s in self.sub_monitors) / self.total
        return my_progress + subprogress

    def update(self, units: int=1, message: Optional[str]=None):
        self.worked += units
        self.progress = self.get_progress()
        if message:
            self.message = message
        self.do_update()

    def do_update(self):
        if self.log:
            name = "{}: ".format(self.name) if self.name is not None else ""
            log.info(LOG_FORMAT.format(self=self, name=name, percent=self.progress*100))
        for listener in self.listeners:
            listener(self)

    def add_listener(self, func):
        self.listeners.add(func)

    def remove_listener(self, func):
        self.listeners.remove(func)

    def submonitor(self, total, *args, **kargs):
        monitor = SubMonitor(self, *args, total=total, **kargs)
        self.sub_monitors.add(monitor)
        return monitor
        
class SubMonitor(ProgressMonitor):
    def __init__(self, super_monitor, log=False, *args, **kargs):
        self.super_monitor = super_monitor
        super(SubMonitor, self).__init__(*args, log=False, **kargs)

    def update(self, units=1, message=None):
        super(SubMonitor, self).update(units, message)

        if self.worked == self.total:
            # We're done. We can deregister ourselves from supermonitor.
            self.super_monitor.sub_monitors.remove(self)
            self.super_monitor.update(1, message)
        else:
            # We're not done; inform super monitor of progress
            self.super_monitor.update(0, message)


class NullMonitor(ProgressMonitor):
    def update(self, *args, **kargs):
        pass

