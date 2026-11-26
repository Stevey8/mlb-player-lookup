# Empty on purpose: pytest's default "prepend" import mode adds the
# directory containing each conftest.py to sys.path. Having this file at
# the repo root means tests/ can `import web` and `import lookup` without
# the repo needing to be an installable package or PYTHONPATH tricks.
