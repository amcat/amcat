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
Helper module for distributing 'trivially parallelizable' tasks over multiple threads
"""
from __future__ import unicode_literals, print_function, absolute_import

from threading import Thread
from Queue import Queue, Empty
import logging; log = logging.getLogger(__name__)
import time

from amcat.tools import toolkit

def _run(queue, action, problems):
    """Get and process tasks from the queue until queue.done (custom attr) is True"""
    while True:
        try:
            task = queue.get(timeout=.1)
        except Empty:
            if getattr(queue, "done", False):
                break
            continue
        try:
            action(task)
        except Exception, e:
            log.error(e, exc_info=True)
            problems.append(task) # list append is thread safe
        finally:
            queue.task_done()

            
def distribute_tasks(tasks, action, nthreads=4, queue_size=10, retry_exceptions=False, batch_size=None):
    """
    Distribute the elements in tasks over a nthreads threads using a queue.
    The trheads will call action(task) on each element in tasks.

    If action(task) raises an exception, the element is placed on the problem
    list. If retry_exceptions is non-False, after all elements are done the problematic
    elements are retried. Otherwise, the list of problems is returned.

    If batch_size is not None, will 'cut' tasks into batches of that size and
    place the sub-sequences on the queue
    """
    starttime = time.time(); count=0
    queue = Queue(queue_size)
    problems = []

    log.debug("Creating and starting {nthreads} threads".format(**locals()))
    action_args =dict(queue=queue, action=action, problems=problems)
    threads = [Thread(name="Worker_%i" % i, target=_run, kwargs=action_args) for i in range(nthreads)]
    for t in threads:
        t.start()

    log.debug("Placing tasks on queue")
    if batch_size:
        for subset in toolkit.splitlist(tasks, batch_size):
            count += len(subset)
            queue.put(subset)
    else:
        for task in tasks:
            queue.put(task)
            count += 1
    
    log.debug("Waiting until queue is empty")
    queue.join()
    
    while problems and retry_exceptions:
        log.debug('Retrying {n} problematic tasks'.format(n=len(problems)))
        # use a temporary list to hold problems and clear problems list before retrying
        _problems = problems[:]
        del problems[:]
        for problem in _problems:
            queue.put(problem)
        queue.join()
        if type(retry_exceptions) == int:
            retry_exceptions -= 1

    queue.done = True
    
    total_time = time.time() - starttime
    rate = count / (total_time + .00001)
    log.debug('Processed {count} tasks in {total_time:.0f} seconds ({rate:.2f}/second)'.format(**locals()))
    
    return problems

    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest, amcatlogging
#amcatlogging.debug_module()

class TestMultithread(amcattest.PolicyTestCase):
    def test_tasks(self):
        """Trivial test"""
        l = []
        distribute_tasks(range(10), l.append)
        self.assertEqual(l, list(range(10)))
        

    def test_multithread(self):
        """Test that work is indeed distributed and that threads are closed off"""
        from threading import current_thread
        from time import sleep
        l = set()
        def action(_x):
            l.add(current_thread())
            time.sleep(.05) # make sure other threads get a chance...
        distribute_tasks(range(10), action)
        self.assertTrue(len(l) > 1)

        time.sleep(.5) # give threads a chance to die
        for t in l:
            self.assertFalse(t.is_alive())

    def test_error(self):
        """Test that even in the case of exceptions all work is done"""
        from random import choice
        l = set()
        def action(x):
            if choice([True, False]):
                raise amcatlogging.SilentException()
            l.add(x)
        tasks = set(range(1000))
        distribute_tasks(tasks, action, retry_exceptions=True)
        self.assertEqual(l, tasks)

    def test_finite_retries(self):
        """Test that a number of retries can be specified"""
        from random import choice
        seen = set()
        def action(x):
            if x % 4 == 0 or (x not in seen and x %2 == 0):
                seen.add(x)
                raise amcatlogging.SilentException()
        n = 100
        tasks = set(range(n))
        problems = distribute_tasks(tasks, action)
        seen = set()
        problems_oneretry = distribute_tasks(tasks, action, retry_exceptions=1)

        self.assertEqual(len(problems), n/2)
        self.assertTrue(len(problems_oneretry), n/4)
        
    def test_batches(self):
        """Test that batch_size works as advertised"""
        l = []
        distribute_tasks(range(100), l.append, batch_size=10)
        self.assertEqual(len(l), 100 / 10)

        self.assertEqual(set(toolkit.flatten(l)), set(range(100)))
        
    
            
