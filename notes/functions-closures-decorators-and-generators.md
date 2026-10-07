# Functions and closures

This is how Python functions and closures work. A `def` statement builds a function object and binds it to a name. The function object holds its bytecode, its `__defaults__`, its `__globals__`, and the cells for free variables. A nested function that uses a name from an outer function is a closure. The outer name lives in a cell, and the inner function's `__closure__` tuple holds that cell. The cell survives after the outer function returns, which is how a factory can return a function that still sees the values it was built with.

Closures capture variables, not the values those variables had at definition time. A loop that builds lambdas `lambda: i` without a default will usually make every lambda see the final `i`, because each lambda reads the same cell. Binding the current value as a default argument, `lambda i=i: i`, snapshots it. The same rule applies to functions defined in a loop that close over the loop variable.

`*args` collects extra positional arguments into a tuple. `**kwargs` collects extra keyword arguments into a dict. A parameter can be keyword-only by placing it after `*`, and positional-only by placing it before `/`. That split is part of the function's public contract: positional-only names can be renamed later without breaking callers, and keyword-only names cannot be passed by accident as a positional.

# Decorators

This is how Python decorators work. A decorator is a callable that takes a function and returns a replacement. The syntax `@deco` above `def f` is exactly `f = deco(f)` after the function object is created. Decorators run at definition time, not at call time. A decorator that prints when applied will print while the module is importing, before anyone calls the function.

Because the replacement is what callers see, a decorator that does not copy metadata hides the original name, signature, and docstring. `functools.wraps(func)` applied to the wrapper copies `__name__`, `__doc__`, `__module__`, and `__wrapped__`. Stacking decorators applies them bottom-up: `@a` then `@b` then `def f` means `f = a(b(f))`. The first wrapper called is the one nearest the `def`.

A decorator factory is a function that returns a decorator, which is why `@repeat(3)` has parentheses and `@repeat` does not. The call `repeat(3)` runs immediately and must return the actual decorator. Class-based decorators implement `__call__` so the instance itself is the wrapper. Use a decorator when the extra behavior is cross-cutting, such as logging, caching with `functools.lru_cache`, or registering the function in a table. Do not use one when an ordinary function call would be easier to read.

# Generators

This is how Python generators work. A function that contains `yield` is a generator function. Calling it does not run the body. It returns a generator object, which is an iterator. Each `next` call runs the body until the next `yield`, sends that value out, and suspends the frame. Local variables stay alive across suspensions. When the function returns, or falls off the end, the generator raises `StopIteration`, and a `for` loop stops.

`yield` is an expression. `value = yield item` pauses, and the caller can push a value in with `generator.send`. `send` both resumes the generator and becomes the result of that `yield`. The first resume must be `next` or `send(None)`, because there is no `yield` waiting yet. `throw` injects an exception at the pause point. `close` raises `GeneratorExit` so a `try`/`finally` inside the generator can release resources.

Generator expressions, `(x * x for x in nums)`, are the same idea in one expression. They are lazy. Nothing is computed until iteration starts, and each element is produced on demand. That matters when the source is large or infinite. A generator is single-use: once it is exhausted, iterating it again does nothing. If you need a second pass, call the generator function again or store the results in a list.
