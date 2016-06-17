from operator import add, mul
from functools import partial

import six
from twisted.trial import unittest
from twisted.internet import defer

from txretry.retry import simpleBackoffIterator, RetryingCall


class TestBackoffIterator(unittest.TestCase):
    """Test the back-off iterator."""

    def testNowDefault(self):
        """When now is not specified, the first delay the iterator returns
        must be zero (in other words we're testing that by default the
        function will be called immediately)."""
        bi = simpleBackoffIterator()
        delay = six.next(bi)
        self.assertEqual(0.0, delay)

    def testNow(self):
        """When now=True is passed to the back-off iterator, the first
        delay it returns must be zero."""
        bi = simpleBackoffIterator(now=True)
        delay = six.next(bi)
        self.assertEqual(0.0, delay)

    def testNotNow(self):
        """When now=False is passed to the back-off iterator, the first
        delay it returns must not be zero."""
        bi = simpleBackoffIterator(now=False)
        delay = six.next(bi)
        self.assertNotEqual(0.0, delay)

    def testInitDelay(self):
        """If an initial delay is passed, it must be the first value
        returned by the iterator."""
        initDelay = 7
        bi = simpleBackoffIterator(now=False, initDelay=initDelay)
        delay = six.next(bi)
        self.assertEqual(initDelay, delay)

    def testDefaultSettingsEventuallyHalt(self):
        """Check that the default iterator raises C{StopIteration}."""

        def exhaust():
            """Set up a default iterator and keep call its next method
            forever. If it doesn't raise this test will never finish."""
            bi = simpleBackoffIterator()
            while True:
                six.next(bi)
        self.assertRaises(StopIteration, exhaust)

    def testDefaultSettingsNoNegativeDelays(self):
        """Ensure no negative values are yielded by the iterator."""
        bi = simpleBackoffIterator()
        for delay in bi:
            self.assertTrue(delay >= 0.0)

    def testMaxResults(self):
        """Ensure the maxResults argument is respected."""
        maxResults = 12
        bi = simpleBackoffIterator(now=False, maxResults=maxResults)
        for _ in range(maxResults):
            six.next(bi)
        with self.assertRaises(StopIteration):
            six.next(bi)

    def testConstant(self):
        """Make a back-off iterator that yields a constant for a certain
        number of times, and check its results."""
        n = 10
        constant = 5.0
        initDelay = 3.0
        bi = simpleBackoffIterator(now=False,
                                   initDelay=initDelay,
                                   incFunc=lambda _: constant,
                                   maxDelay=10.0,
                                   maxResults=n + 1)
        self.assertEqual(initDelay, six.next(bi))
        for _ in range(n):
            self.assertEqual(constant, six.next(bi))

    def testMul3(self):
        """Make a back-off iterator whose increment function multiplies the
        previous delay by 3 and check its results."""
        bi = simpleBackoffIterator(now=False,
                                   initDelay=1.0,
                                   incFunc=partial(mul, 3.0),
                                   maxDelay=10.0,
                                   maxResults=10)
        self.assertEqual(1.0, six.next(bi))
        self.assertEqual(3.0, six.next(bi))
        self.assertEqual(9.0, six.next(bi))

    def testAdd3(self):
        """Make a back-off iterator whose increment function adds 3 to the
        previous delay and check its results."""
        bi = simpleBackoffIterator(now=False,
                                   initDelay=2.0,
                                   incFunc=partial(add, 3.0),
                                   maxDelay=10.0,
                                   maxResults=10)
        self.assertEqual(2.0, six.next(bi))
        self.assertEqual(5.0, six.next(bi))
        self.assertEqual(8.0, six.next(bi))

    def testMaxDelay(self):
        """Make a back-off iterator whose increment function multiplies the
        previous delay by 3 and check that it returns the passed maxDelay
        value once the delay would be too large."""
        bi = simpleBackoffIterator(now=False,
                                   initDelay=1.0,
                                   incFunc=partial(mul, 3.0),
                                   maxDelay=10.0,
                                   maxResults=10)
        self.assertEqual(1.0, six.next(bi))
        self.assertEqual(3.0, six.next(bi))
        self.assertEqual(9.0, six.next(bi))
        self.assertEqual(10.0, six.next(bi))
        self.assertEqual(10.0, six.next(bi))


class _InitiallyFailing(object):
    """
    Provide a callable that raises an exception for its first C{nFails}
    calls, and then returns the passed result.

    @param nFails: an C{int} specifying how many times to initially fail.
    @param result: the result to return after the initial failures.
    @param exceptionList: a list of exceptions to return (in order) initially.
    """
    def __init__(self, nFails, result=None, exceptionList=None):
        assert nFails >= 0
        self._nFails = nFails
        self._result = result
        self._exceptionList = exceptionList or []
        self._failCount = 0
        self._succeeded = False

    def __call__(self):
        """The function was called. Raise if we still need to, else return
        the eventual result.

        @raise: an exception from C{self._exceptionList} if we are still
            expected to fail.
        @return: C{self._result}, the value we were given on construction.
        """
        # Make sure we only succeed once.
        assert self._succeeded is False
        if self._failCount < self._nFails:
            try:
                excClass = self._exceptionList[self._failCount]
            except IndexError:
                excClass = Exception
            self._failCount += 1
            raise excClass()
        else:
            self._succeeded = True
            return self._result


class _CallCounter(object):
    """Provide a callable that counts the number of times it is invoked."""
    def __init__(self):
        self._nCalls = 0

    def __call__(self, result):
        """A function call has been made. Count it.

        @param result: The function argument.
        @return: The result we were called with.
        """
        self._nCalls += 1
        return result

    def assertCalledOnce(self):
        """Make sure we were called exactly once."""
        assert self._nCalls == 1


class _ValueErrorThenNameErrorRaiser(object):
    """Provide a callable that raises C{ValueError} on its first invocation
    and a C{NameError} thereafter."""
    def __init__(self):
        self._called = False

    def __call__(self):
        """A function call has been made. Raise an appropriate exception."""
        if self._called:
            raise NameError()
        else:
            self._called = True
            raise ValueError()


class TestRetryingCall(unittest.TestCase):
    """Test the RetryingCall class."""

    def testSimplestNoFailure(self):
        """A (retrying) call to a function that returns a constant should
        return that constant and should encounter no failures."""

        rc = RetryingCall(lambda: 20)

        def _check(result):
            self.assertEqual(20, result)
            self.assertEqual([], rc.failures)

        d = rc.start()
        d.addCallback(_check)
        return d

    def testSimplestDeferredReturner(self):
        """Test a C{Deferred} returning function that returns a constant."""
        rc = RetryingCall(lambda: defer.succeed(15))
        d = rc.start()
        d.addCallback(lambda result: self.assertEqual(15, result))
        return d

    def testSimpleDeferredReturner(self):
        """Test that adding a callback to the C{Deferred} returned by
        C{start} works as expected."""

        def _ret(result):
            self.assertEqual(result, 200)
            return 'floopy'

        rc = RetryingCall(lambda: defer.succeed(200))
        d = rc.start()
        d.addCallback(_ret)
        d.addCallback(lambda r: self.assertEqual(r, 'floopy'))
        return d

    def testInitiallyFailingNoFailures(self):
        """Test the C{_InitiallyFailing} class when it is told not to fail."""
        f = _InitiallyFailing(0)
        rc = RetryingCall(f)
        d = rc.start()
        d.addCallback(lambda _: self.assertEqual([], rc.failures))
        return d

    def testSimplePositionalArgs(self):
        """Check that positional arguments we give to the constructor are
        passed to the function when it is called."""
        rc = RetryingCall((lambda *x: x), 9, 10, 11)
        d = rc.start()
        d.addCallback(lambda result: self.assertEqual((9, 10, 11), result))
        return d

    def testSimpleKeywordArgs(self):
        """Check that keyword arguments we give to the constructor are
        passed to the function when it is called."""
        rc = RetryingCall((lambda xxx, yyy: (yyy, xxx)), xxx=10, yyy='no!')
        d = rc.start()
        d.addCallback(lambda result: self.assertEqual(('no!', 10), result))
        return d

    def testSimplePositionalAndKeywordArgs(self):
        """Check that positional and keyword arguments given to the
        constructor are passed to the function when it is called."""
        rc = RetryingCall((lambda x, y=None: (x, y)), 9, y='hey')
        d = rc.start()
        d.addCallback(lambda r: self.assertEqual(r, (9, 'hey')))
        return d

    def testIgnoreRegularException(self):
        """Use a failure tester that ignores C{Exception} with an
        C{_InitiallyFailing} instance that raises 3 errors before returning
        the correct result."""

        def _failureTester(f):
            """Return C{None} on any C{Exception} failure.

            @param f: a C{Failure}.
            @return: C{None} if C{f} is an C{Exception} failure,
                else return C{f}.
            """
            f.trap(Exception)
        f = _InitiallyFailing(3, result=5)
        rc = RetryingCall(f)
        d = rc.start(failureTester=_failureTester)
        d.addCallback(lambda result: self.assertEqual(5, result))
        d.addCallback(lambda _: self.assertEqual(3, len(rc.failures)))
        return d

    def test1ValueError(self):
        """Call a function that initially fails with a C{ValueError}
        and then returns a result.
        """

        def _failureTester(f):
            """Return C{None} on any C{ValueError} failure.

            @param f: a C{Failure}.
            @return: C{None} if C{f} is an C{ValueError} failure,
                else return C{f}.
            """
            f.trap(ValueError)
        f = _InitiallyFailing(1, result=5, exceptionList=[ValueError])
        rc = RetryingCall(f)
        d = rc.start(failureTester=_failureTester)
        d.addCallback(lambda result: self.assertEqual(5, result))
        d.addCallback(lambda _: self.assertEqual(1, len(rc.failures)))
        return d

    def test3ValueErrors(self):
        """Call a function that initially fails three times with
        C{ValueError}s and then returns a result.
        """

        def _failureTester(f):
            """Return C{None} on any C{ValueError} failure.

            @param f: a C{Failure}.
            @return: C{None} if C{f} is an C{ValueError} failure,
                else return C{f}.
            """
            f.trap(ValueError)
        f = _InitiallyFailing(3, result=7, exceptionList=[ValueError] * 3)
        rc = RetryingCall(f)
        d = rc.start(failureTester=_failureTester)
        d.addCallback(lambda result: self.assertEqual(7, result))
        d.addCallback(lambda _: self.assertEqual(3, len(rc.failures)))
        return d

    def testDontAllowKeyError(self):
        """Call a function that fails with a C{KeyError}s but with a
        failure tester that only ignores C{ValueError} and check that the
        call fails with a C{KeyError}.
        """

        def _failureTester(f):
            """Return C{None} on any C{ValueError} failure.

            @param f: a C{Failure}.
            @return: C{None} if C{f} is an C{ValueError} failure,
                else return C{f}.
            """
            f.trap(ValueError)
        f = _InitiallyFailing(3, exceptionList=[KeyError])
        rc = RetryingCall(f)
        d = rc.start(failureTester=_failureTester)
        self.failUnlessFailure(d, KeyError)
        return d

    def testValueErrorThenNameError(self):
        """Call a function that fails first with a C{ValueError} and then
        with a C{NameError} before returning its result.
        """

        def _failureTester(f):
            """Return C{None} on any C{ValueError} or C{NameError} failure.

            @param f: a C{Failure}.
            @return: C{None} if C{f} is a C{ValueError} or C{NameError}
                failure, else return C{f}.
            """
            if not f.check(ValueError, NameError):
                return f
        f = _InitiallyFailing(2, result=15,
                              exceptionList=[ValueError, NameError])
        rc = RetryingCall(f)
        d = rc.start(failureTester=_failureTester)
        d.addCallback(lambda result: self.assertEqual(15, result))
        d.addCallback(lambda _: self.assertEqual(2, len(rc.failures)))
        return d

    def testListBackoffIteratorAsList(self):
        """Pass a back-off iterator that is a C{list} and make sure the
        function is called without incident until the list is exhausted."""
        rc = RetryingCall(lambda: defer.fail(Exception()))
        d = rc.start(backoffIterator=[0.05, 0.06, 0.07])
        self.failUnlessFailure(d, Exception)
        return d

    def testListBackoffIteratorAsTuple(self):
        """Pass a back-off iterator that is a C{tuple} and make sure the
        function is called without incident until the list is exhausted."""
        rc = RetryingCall(lambda: defer.fail(Exception()))
        d = rc.start(backoffIterator=(0.01, 0.01, 0.01))
        self.failUnlessFailure(d, Exception)
        return d

    def testExactlyOneSuccessfulCall(self):
        """Ensure that a function that returns a result is only called once."""
        f = _CallCounter()
        rc = RetryingCall(f, 99)
        d = rc.start()
        d.addCallback(lambda result: self.assertEqual(99, result))
        d.addCallback(lambda _: f.assertCalledOnce())
        return d

    def testFirstFailureReceived(self):
        """Ensure that the first failure encountered is the one that
        is passed to the errback when the retrying call gives up."""
        f = _ValueErrorThenNameErrorRaiser()
        rc = RetryingCall(f)
        d = rc.start(backoffIterator=(0.01, 0.01, 0.01))
        self.failUnlessFailure(d, ValueError)
        return d
