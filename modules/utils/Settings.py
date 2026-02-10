from typing import Optional, Union

from configobj import ConfigObj
from readerwriterlock import rwlock


class Settings:
    _config_object: ConfigObj = None
    _instance = None

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = rwlock.RWLockFair()
            cls._instance._rlock = cls._instance._lock.gen_rlock()
            cls._instance._wlock = cls._instance._lock.gen_wlock()

        return cls._instance

    def __init__(self, config: ConfigObj):
        with self._wlock:
            self._config_object = config

    def get_value(self, key: str, section: Optional[str] = None, subsection: Optional[str] = None) -> Union[str, None]:
        value: Union[str, None] = None

        with self._rlock:
            if section is not None:
                if subsection is not None:
                    value = self._config_object[section][subsection][key]
                else:
                    value = self._config_object[section][key]
            else:
                value = self._config_object[key]

        return value
