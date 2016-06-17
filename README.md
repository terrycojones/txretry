`txretry` provides a Twisted class, `RetryingCall`, that calls a function
until it succeeds. A back-off iterator (a generator function that yields
intervals) can be specified to customize the interval between retried
calls.  When/if the back-off iterator raises `StopIteration` the attempt to
call the function is aborted. An instance of the `RetryingCall` class
provides a `start` method that returns a `Deferred` that will fire with the
function result or errback with the first failure encountered.

Usage of the class is described in the following blog post:
http://blogs.fluidinfo.com/terry/2009/11/12/twisted-code-for-retrying-function-calls/
