import os
import glob

modules = glob.glob(os.path.dirname(__file__) + "/*.py")
__all__ = [os.path.basename(f)[:-3] for f in modules if not f.endswith("__init__.py")]

for module in __all__:
    try:
        exec(f"from .{module} import *")
    except Exception as e:
        print(f"Failed to import {module}: {e}")
