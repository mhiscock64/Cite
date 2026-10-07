# The global interpreter lock

This is how the Python GIL works. CPython protects its internal object structures with the global interpreter lock. Only one thread at a time holds the GIL and runs Python bytecode. A thread that is waiting on I/O, or that is inside a C extension which explicitly releases the GIL, lets another thread run. NumPy and many file and socket operations do release it. Pure Python loops do not.

Threads are therefore a good fit for overlapping I/O and a poor fit for speeding up CPU-bound Python. Two threads parsing sockets can make progress while each waits. Two threads doing pure arithmetic on Python objects will mostly take turns, and can be slower than one thread because of lock traffic. For CPU-bound work, use `multiprocessing`, which starts separate interpreters with separate GILs and passes data by pickling, or move the hot loop into a library that releases the GIL. Python 3.13 can be built free-threaded, without a GIL, as an optional build. That build is not the default, and code that assumed the GIL provided atomicity has to be reviewed.

The GIL is not a lock around your data structures. It does not make `self.items.append(x)` followed by a read in another thread a logical transaction you can reason about at the Python level for compound updates. A check-then-act sequence, such as "if key not in cache, compute and store", can interleave. Use a `threading.Lock` around the invariant, or a queue that owns the hand-off. `queue.Queue` is the usual way to pass work between threads without sharing a list.

# asyncio

This is how Python asyncio works. `asyncio` is cooperative concurrency on one thread. A coroutine is a function defined with `async def`. Calling it returns a coroutine object and does not run the body. The event loop runs tasks. At each `await`, the task suspends and the loop can run another task that is ready. There is no preemption. A CPU loop that never awaits, or a call to `time.sleep`, or a blocking socket read, stalls every task on that loop until it returns.

The loop is started with `asyncio.run(main())` from synchronous code. That call creates the loop, runs the coroutine, cancels leftovers, and closes the loop. Inside async code, start sibling work with `asyncio.create_task`, and wait for it with `await`. `asyncio.gather` waits for several awaitables and collects results. If you need a timeout, `asyncio.wait_for` or `asyncio.timeout` cancels the inner task when time is up. Cancellation shows up as `CancelledError` at the next `await`.

Blocking libraries do not become async because you call them from a coroutine. Wrap them with `asyncio.to_thread`, which runs the call in a worker thread and awaits the result, or use an async client that actually awaits socket operations. Share data carefully: the loop is single-threaded, so between `await` points your code is atomic with respect to other tasks. Across an `await`, any task can run, so an invariant that must hold over that gap still needs a design, often an `asyncio.Lock`.

# Processes and the process pool

`concurrent.futures.ProcessPoolExecutor` runs callables in child processes. The arguments and the return value must be picklable. The child imports the module, so the target function should be a top-level function, not a lambda or a nested function. This sidesteps the GIL because each process has its own interpreter. The cost is startup and serialization. Use it for chunky CPU work, not for millions of tiny calls.

Processes do not share memory with the parent. A mutable object passed in is copied by pickle, and mutations in the child are not visible in the parent unless you send them back as a return value or through a `multiprocessing.Queue`. That isolation is the point. It removes data races, and it forces the boundary to be explicit. Prefer this over threads when the work is Python bytecode and the units of work are large enough to pay for the process.
