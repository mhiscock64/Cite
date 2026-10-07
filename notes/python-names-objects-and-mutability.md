# Names are bindings, not boxes

This is how Python names and objects work. A Python name does not contain a value. It is an entry in a namespace that points at an object. Assignment, `x = 1`, looks up or creates the name `x` in the local namespace and binds it to the integer object `1`. The next assignment, `x = x + 1`, builds a new integer and rebinds the name. The old integer is unchanged. This is why `id(x)` often changes after an arithmetic update, and why two names can refer to one object without either "owning" a copy.

The language resolves names with the LEGB rule: local, then enclosing function scopes, then the module global, then builtins. Inside a function, a name is local for the whole function if it is assigned anywhere in that function, unless it is declared `global` or `nonlocal`. Reading a local name before it is bound raises `UnboundLocalError`, even if a global of the same name exists. `global` rebinds the module attribute. `nonlocal` rebinds the nearest enclosing function scope, which is how a nested function keeps a counter without a class.

Identity and equality are different questions. `is` asks whether two names point at the same object. `==` asks whether `__eq__` considers the values equal. CPython interns small integers and some strings, so `a is b` can be true for those by accident. That is an implementation detail, not a rule to rely on. Use `is` for `None`, `True`, and `False`, and for sentinel objects you created yourself.

# Mutability, aliases, and copies

An object is mutable when its contents can change without the object's identity changing. Lists, dicts, sets, and most class instances are mutable. Integers, strings, tuples, and frozensets are not. A tuple can still contain a list, and that inner list can be mutated. Immutability of the container is not deep immutability of everything it references.

Aliasing is the usual source of surprising shared state. If `b = a` and `a` is a list, `b.append(1)` is visible through `a`, because both names point at one list. A shallow copy (`list(a)`, `a.copy()`, or `copy.copy`) makes a new container of the same references. A deep copy (`copy.deepcopy`) walks nested containers and builds new ones. Slices of a list are shallow copies: `a[:]` does not copy the objects inside `a`.

Function default arguments are evaluated once, when the `def` statement runs, not on each call. A default of `[]` or `{}` is therefore one shared mutable object for every caller that omits the argument. Append to it and the next call sees the previous items. The usual fix is a sentinel default of `None` and a fresh list created inside the function body. The same trap appears on classes: a mutable class attribute is shared by every instance that does not shadow it on `self`.
