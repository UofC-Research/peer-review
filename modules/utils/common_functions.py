from importlib import import_module
from types import ModuleType
from typing import Any


# a file that contains common functions that interacts with different objects
def import_class(path: str) -> Any:
    module_path, _, class_name = path.rpartition('.')
    class_: Any
    try:
        # Import and return a module defined in the given path.
        module: ModuleType = import_module(module_path)
        try:
            class_ = getattr(module, class_name)
        except AttributeError:
            raise RuntimeError(f'Class does not exist: {class_name}')
    except ImportError:
        raise RuntimeError(f'Module does not exist: {module_path}')
    return class_
