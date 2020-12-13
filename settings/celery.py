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
from kombu import Exchange, Queue

from settings import get_amcat_config

amcat_config = get_amcat_config()

broker_url = 'pyamqp://'
result_backend = 'redis://'

_qname = amcat_config["celery"].get('queue')
task_queues = (
    Queue(_qname, Exchange('default'), routing_key=_qname),
)
task_default_queue = _qname
task_default_exchange_type= 'direct'
task_default_routing_key = _qname


task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']

task_ignore_result = False
