# Copyright 2011 Fluidinfo Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You
# may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

from operator import mul
from functools import partial
import time

import six
from twisted.internet import reactor, defer, task
from twisted.python import log, failure


def simpleBackoffIterator(maxResults=10, maxDelay=120.0, now=True,
                          initDelay=0.01, incFunc=None):
    """
    Return a generator that produces back-off delay intervals for use with
    a L{RetryingCall}.

    @param maxResults: the maximum number of delays to yield.
    @param maxDelay: the longest delay (in seconds) to yield.
    @param now: if C{True}, immediately yield a delay of zero.
    @param initDelay: the initial delay.
    @param incFunc: a function of one argument (the latest delay), which
        returns the next delay. Default: double the previous delay.
    @return: a generator function that yields C{float} delays.
    """
    assert maxResults > 0
    remaining = maxResults
    delay = initDelay
    incFunc = incFunc or partial(mul, 2.0)

    if now:
        yield 0.0
        remaining -= 1

    while remaining > 0:
        if delay < maxDelay:
            value = delay
        else:
            value = maxDelay
        yield value
        delay = incFunc(delay)
        remaining -= 1


class RetryingCall(object):
    """
    Calls a function repeatedly, passing it args and kw args. Failures are
    passed to a user-supplied failure testing function. If the failure is
    ignored, the function is called again after a delay whose duration is
    obtained from a user-supplied iterator. The start method (below)
    returns a deferred that fires with the eventual non-error result of
    calling the supplied function, or fires its errback if no successful
    result can be obtained before the delay backoff iterator raises
    StopIteration.

    @ival failures: a list of failures received in calling the function.
    @param func: The function to call.
    @param args: Positional arguments to pass to the function.
    @param kw: Keyword arguments to pass to the function.
    """
    def __init__(self, func, *args, **kw):
        self._func = func
        self._args = args
        self._kw = kw
        self._start = time.time()
        self.failures = []

    def _err(self, fail):
        """An errback function for the function call.

        If calling the failure tester raises an error or if the failure
        tester returns a failure, trigger our deferred with the failure.
        Otherwise, arrange for our function to be called again.
        """
        self.failures.append(fail)
        try:
            result = self._failureTester(fail)
        except:
            self._deferred.errback()
        else:
            if isinstance(result, failure.Failure):
                # The failure tester returned a failure. We're done.
                # Give the failure to our deferred.
                self._deferred.errback(result)
            else:
                # Schedule another call.
                log.msg('RetryingCall: Ignoring failure %s' % (fail,))
                self._call()

    def _call(self):
        """
        After the next delay amount, call our function.
        """
        try:
            delay = six.next(self._backoffIterator)
        except StopIteration:
            log.msg('StopIteration in RetryingCall: ran out of attempts.')
            self._deferred.errback(self.failures[0] if self.failures else None)
        else:
            d = task.deferLater(reactor, delay,
                                self._func, *self._args, **self._kw)
            d.addCallbacks(self._deferred.callback, self._err)

    def start(self, backoffIterator=None, failureTester=None):
        """
        Start trying and retrying, if needed, a call to the self._func
        function.

        @param backoffIterator: An iterator that produces delay intervals
            to wait between calls.
        @param failureTester: A function of one
            argument (a C{failure.Failure}) that we can use to check
            whether a failed call should be retried.
        @return: a C{Deferred} that will fire with the result of calling
            self._func with self._args and self._kw as arguments, or fail
            with the first failure encountered.
        """
        self._backoffIterator = iter(backoffIterator or
                                     simpleBackoffIterator())
        self._failureTester = failureTester or (lambda _: None)
        self._deferred = defer.Deferred()
        self._call()
        return self._deferred
