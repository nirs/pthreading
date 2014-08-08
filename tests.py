#
# Copyright 2012 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#
import functools
import threading
import unittest
import logging
from time import sleep
import sys

import pthreading


class TestCaseBase(unittest.TestCase):
    log = logging.getLogger('test')


def without_module(name):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*a, **kw):
            module = sys.modules.pop(name)
            try:
                return f(*a, **kw)
            finally:
                sys.modules[name] = module
        return wrapper
    return decorator


class WithoutModuleTests(TestCaseBase):

    def setUp(self):
        self.assertIn('sys', sys.modules)

    def tearDown(self):
        self.assertIn('sys', sys.modules)

    @without_module('sys')
    def testWithout(self):
        self.assertNotIn('sys', sys.modules)


class MonkeyPatchTests(TestCaseBase):

    def tearDown(self):
        pthreading._is_monkey_patched = False

    @without_module('thread')
    @without_module('threading')
    def testMonkeyPatch(self):
        pthreading.monkey_patch()
        self.checkMonkeyPatch()

    @without_module('thread')
    @without_module('threading')
    def testMonkeyPatchTwice(self):
        pthreading.monkey_patch()
        pthreading.monkey_patch()
        self.checkMonkeyPatch()

    @without_module('thread')
    def testMonkeyPatchRaisesThread(self):
        assert 'threading' in sys.modules
        self.assertRaises(RuntimeError, pthreading.monkey_patch)

    @without_module('threading')
    def testMonkeyPatchRaisesThreading(self):
        assert 'thread' in sys.modules
        self.assertRaises(RuntimeError, pthreading.monkey_patch)

    def checkMonkeyPatch(self):
        import thread
        import threading
        self.assertEquals(thread.allocate_lock, pthreading.Lock)
        self.assertEquals(threading.Lock, pthreading.Lock)
        self.assertEquals(threading.RLock, pthreading.RLock)
        self.assertEquals(threading.Condition, pthreading.Condition)


class LockTests(TestCaseBase):
    def _testAcquire(self, lock):
        self.assertTrue(lock.acquire())

    def _testRelease(self, lock):
        lock.acquire()
        lock.release()
        self.assertTrue(lock.acquire(False))

    def testAcquireLock(self):
        self._testAcquire(pthreading.Lock())

    def testAcquireRLock(self):
        self._testAcquire(pthreading.RLock())

    def testReleaseLock(self):
        self._testRelease(pthreading.Lock())

    def testReleaseRLock(self):
        self._testRelease(pthreading.RLock())

    def testAcquireNonblocking(self):
        lock = pthreading.Lock()
        lock.acquire()
        self.assertFalse(lock.acquire(False))

    def testAcquireRecursive(self):
        lock = pthreading.RLock()
        self.assertTrue(lock.acquire())
        self.assertTrue(lock.acquire(False))

    def testLocked(self):
        lock = pthreading.Lock()
        self.assertFalse(lock.locked())
        with lock:
            self.assertTrue(lock.locked())
        self.assertFalse(lock.locked())


class Flag(object):
    def __init__(self):
        self._flag = False

    def __nonzero__(self):
        return self._flag

    def set(self):
        self._flag = True

    def clear(self):
        self._flag = False


class ConditionTests(TestCaseBase):
    def testBaseTest(self, lock=None, timeout=None):
        """
        Base Condition exerciser
        """
        flag = Flag()
        c = pthreading.Condition(lock)

        def setter(flag):
            sleep(2)
            with c:
                flag.set()
                c.notify()
        threading.Thread(target=setter, args=(flag,)).start()
        with c:
            while not flag:
                self.log.debug("main waits")
                c.wait(timeout)

        self.assertTrue(flag)

    def testNotifyAll(self, lock=None):
        """
        Exercise Condition.notifyAll()
        """
        flag = Flag()
        c = pthreading.Condition(lock)

        def setter(flag):
            sleep(2)
            with c:
                flag.set()
                c.notifyAll()
        threading.Thread(target=setter, args=(flag,)).start()
        with c:
            while not flag:
                c.wait()

        self.assertTrue(flag)

    def testXWait(self, lock=None):
        """
        Exercise Condition.wait() with 1s timeout that never become true
        """
        self.log.info("Creating Condition object")
        flag = Flag()
        c = pthreading.Condition(lock)
        tired = 0
        with c:
            while not flag and tired < 5:
                self.log.debug("main waits")
                c.wait(1)
                tired = 5

        self.assertFalse(flag)

    def testNotify(self):
        """
        Exercise Condition.notify()
        """
        self.testBaseTest()

    def testWaitIntegerTimeout(self):
        """
        Exercise Condition.wait() with 1s timeout
        """
        self.testBaseTest(timeout=1)

    def testWaitFloatTimeout(self):
        """
        Exercise Condition.wait() with 0.3s timeout (fraction of a second)
        """
        self.testBaseTest(timeout=0.3)

    def testNotifyWithUserProvidedLock(self):
        """
        Exercise Condition.notify()
        """
        self.testBaseTest(lock=pthreading.Lock())

    def testWaitIntegerTimeoutWithUserProvidedLock(self):
        """
        Exercise Condition.wait() with 1s timeout
        """
        self.testBaseTest(lock=pthreading.Lock(), timeout=1)

    def testWaitFloatTimeoutWithUserProvidedLock(self):
        """
        Exercise Condition.wait() with 0.3s timeout (fraction of a second)
        """
        self.testBaseTest(lock=pthreading.Lock(), timeout=0.3)

    def testNotifyWithUserProvidedRLock(self):
        """
        Exercise Condition.notify()
        """
        self.testBaseTest(lock=pthreading.RLock())

    def testWaitIntegerTimeoutWithUserProvidedRLock(self):
        """
        Exercise Condition.wait() with 1s timeout
        """
        self.testBaseTest(lock=pthreading.RLock(), timeout=1)

    def testWaitFloatTimeoutWithUserProvidedRLock(self):
        """
        Exercise Condition.wait() with 0.3s timeout (fraction of a second)
        """
        self.testBaseTest(lock=pthreading.RLock(), timeout=0.3)


class EventTests(TestCaseBase):
    def _test(self, timeout):
        self.log.info("Creating Event object")
        e = pthreading.Event()

        def setter():
            self.log.info("Setter thread is sleeping")
            sleep(2)
            self.log.info("Setter thread is setting")
            e.set()
            self.log.info("Event object is set (%s) :D", e.is_set())

        self.log.info("Starting setter thread")
        threading.Thread(target=setter).start()
        self.log.info("Waiting for salvation")
        res = e.wait(timeout)
        self.assertTrue(res is not False)

    def testPassWithTimeout(self):
        self._test(5)

    def testPassWithoutTimeout(self):
        self._test(None)

    def testNotPassTimeout(self):
        self.log.info("Creating Event object")
        e = pthreading.Event()
        self.log.info("Waiting for salvation (That will never come)")
        res = e.wait(0.5)
        self.assertFalse(res)

    def testZeroTimeout(self):
        self.log.info("Creating Event object")
        e = pthreading.Event()
        self.log.info("Waiting 0 for salvation (That will never come)")
        res = e.wait(0)
        self.assertFalse(res)

if __name__ == '__main__':
    unittest.main()
