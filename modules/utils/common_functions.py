from importlib import import_module
from types import ModuleType
from typing import Any, List, Optional

from modules.behavioural.database.query import Query


# a file that contains common functions that interacts with different objects
def import_class(path: str) -> Any:
    """
    Imports a class from a string path and returns the class object. The path must be a
    string in the format 'module.submodule.classname'. If the class or module does not
    exist, an error will be raised.

    :param path: The dotted string path to the class to be imported.
    :type path: str
    :return: The class object specified by the given path.
    :rtype: Any
    :raises ImportError: If the specified module does not exist.
    :raises RuntimeError: If the specified class does not exist in the module.
    """
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
        raise ImportError(f'Module does not exist: {module_path}')
    return class_


def create_queries(path: str, *args, **kwargs) -> Optional[List[Query]]:
    class_ = import_class(path)

    return [class_(*args, **kwargs)]
