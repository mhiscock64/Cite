# Type hints are annotations

This is how Python type hints work. Type hints describe objects for readers and for tools. CPython does not check them when a function is called, unless you add a separate checker such as mypy or pyright, or a runtime library that inspects annotations. Annotations are stored on the function as `__annotations__`. Since Python 3.7, `from __future__ import annotations` postpones evaluation so annotations are kept as strings, which lets a hint mention a class that is defined later in the file.

Modern syntax is built in. `list[int]` and `dict[str, int]` have worked since 3.9, so `typing.List` is unnecessary. `int | None` has worked since 3.10, so `Optional[int]` is unnecessary. `tuple[int, ...]` means a tuple of any length of ints. `tuple[int, str]` means exactly two items of those types. Use `Any` only when you truly accept every object. Prefer a precise element type on collections, because a bare `list` hides what the code is allowed to put in it.

`TypeVar` and, since 3.12, the statement `type` and the syntax `def first[T](items: list[T]) -> T` introduce a generic. The same `T` in the argument and the return means the output type tracks the input type. A constrained type variable, `T = TypeVar("T", int, str)`, accepts only those types. A bound, `T = TypeVar("T", bound=HasName)`, accepts any subtype of that bound.

# Dataclasses

This is how Python dataclasses work. `@dataclass` generates `__init__`, `__repr__`, and `__eq__` from class attributes that have annotations. Fields are declared in the class body, not assigned inside `__init__`. A default is written as `count: int = 0`. A mutable default must be wrapped in `field(default_factory=list)` so each instance gets its own list. The generated `__init__` takes fields in declaration order, and fields with defaults must follow fields without them, the same rule as ordinary functions.

`frozen=True` makes instances read-only after construction and generates a hash if the fields are hashable, which lets the instance be a dict key or a set member. `slots=True` stores fields in `__slots__` instead of a per-instance `__dict__`, which uses less memory and blocks accidental attributes. `order=True` adds comparison methods based on the field tuple. `kw_only=True` forces callers to pass field names.

A dataclass is still an ordinary class. You can write methods, override `__post_init__` to validate or to fill a field that depends on others, and inherit. Inheritance concatenates fields: base fields come first. If you need a custom `__init__` while keeping the rest of the generation, set `init=False` or write the method yourself. Prefer a dataclass over a hand-written carrier class when the type is mostly data with a little behavior.

# Protocols and structural typing

This is how Python protocols work. A `Protocol` describes the methods and attributes an object must have, without requiring a shared base class. A class matches the protocol if it has those members, even if it never inherits from the protocol. That is structural typing, the same idea as duck typing, checked by a type checker. `runtime_checkable` lets `isinstance` look for the methods, but that check is shallow: it does not verify argument types.

Use a Protocol when you want to accept any object with a small shape, such as "has a `read(self, n: int) -> bytes` method", including objects from libraries you do not control. Use a nominal base class, an ABC, when you want registration, shared implementation, or an explicit opt-in. `Iterable[int]`, `Mapping[str, int]`, and `Sequence[int]` are protocols already. Accepting a `Sequence` instead of a `list` lets a tuple or a range work without a copy.

`TypedDict` describes a dict with known keys and value types. It does not create a new runtime type. A `TypedDict` is still a dict, and extra keys are a type-checker concern, not a runtime error, unless you validate the payload yourself. Use it at boundaries, such as a JSON object, and convert to a dataclass once the data is inside the program.
