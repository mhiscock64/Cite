# Modules and the import system

This is how Python imports work. A module is an object of type `module`. Its namespace is the module's `__dict__`. `import math` finds the module, executes it if this is the first import, stores the module object in `sys.modules`, and binds the local name `math` to that object. A later import of the same module returns the cached object and does not run the body again. That cache is why a module's top-level code is initialization, and why mutating a module global is visible to every importer.

`from pkg.mod import name` still loads the module. It then binds `name` in the local namespace to whatever object `name` referred to at import time. If the module later rebinds its own global, the importer keeps the original object. If the object is mutable and the module mutates it in place, the importer sees the mutation. Circular imports fail when module A, while still executing, imports module B, which tries to read a name from A that has not been assigned yet. The usual fix is to move the import inside the function that needs it, or to split the shared names into a third module.

Packages are modules that can contain other modules. A regular package has an `__init__.py`, which runs when the package is imported. A namespace package, from PEP 420, has no `__init__.py` and can be split across several directories on `sys.path`. Relative imports, `from . import sibling` or `from ..other import name`, only work inside a package. They use the current module's `__package__`. A script run as a file has `__name__ == "__main__"` and no package, so relative imports fail there. Run it as `python -m package.mod` if it needs to be a package member.

# How import finds code

Import uses finders and loaders. `sys.meta_path` holds meta path finders. The default ones look at frozen modules, built-in modules, and then `sys.path`. `sys.path` starts with the script's directory, or the empty string for the current directory, then `PYTHONPATH`, then the standard library and site-packages. The first match wins. A name collision between your `json.py` and the standard library `json` is resolved by whichever directory appears first, which is a common way to shadow a stdlib module by accident.

A finder returns a module spec. The loader creates the module, inserts it into `sys.modules` early so circular imports can see a partial module, then executes the code in that module's namespace. Importlib is the public API for this. `importlib.import_module("pkg.mod")` imports by string. `importlib.reload` runs the module again, but existing `from mod import name` bindings and existing instances are not updated. Reload is a development tool, not a design you should depend on.

# Environments and project metadata

A virtual environment is a directory with its own `python` and `site-packages`. Activating it puts that `python` first on `PATH`. The standard library stays shared with the interpreter that created the environment. Dependencies installed into the environment are not visible to other environments, which is what keeps one project's pins from changing another project. Create one with `python -m venv .venv`.

`pyproject.toml` is the project file. The `[project]` table holds the name, version, and dependencies. `[build-system]` names the build backend, such as setuptools, hatchling, or flit. An editable install, `pip install -e .`, puts a link to the project on `sys.path` so source edits are imported immediately. Lock files, produced by tools such as pip-tools, uv, or poetry, pin the full transitive graph so two machines install the same wheels. Declare runtime dependencies in the project table, and keep test and lint tools in a dependency group so library users do not have to install them.
