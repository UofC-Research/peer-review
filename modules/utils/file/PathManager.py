from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from readerwriterlock import rwlock


# TODO: Need to change to dataclass


class PathManager:
    _instance = None

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = rwlock.RWLockFair()
            cls._rlock = cls._lock.gen_rlock()
            cls._wlock = cls._lock.gen_wlock()

        return cls._instance

    def __init__(self):
        self._base_path_name: Union[str, None] = None
        self._path: Union[str, None] = None
        self._filename: Union[str, None] = None

    def set_base_path_name(self, base_path: str) -> None:
        if not base_path.endswith('/'):
            base_path = base_path + '/'
        with PathManager._wlock:
            self._base_path_name = base_path
            p = Path(base_path)
            p.mkdir(parents=True, exist_ok=True)

    def get_base_path_name(self) -> str:
        with PathManager._rlock:
            return self._base_path_name

    def set_path(self, path: str) -> None:
        with PathManager._wlock:
            if not path.endswith('/'):
                path = path + '/'
            self._path = path

    def get_path(self, base_path: str = '') -> str:
        if self._path is None:
            self.set_path(f'{datetime.now(timezone.utc):%Y-%m-%D %H.%M.%S%z}/')
        p = Path(f'{base_path}{self._path}')
        p.mkdir(parents=True, exist_ok=True)
        return f'{base_path}{self._path}'

    def set_filename(self, filename: str) -> None:
        with PathManager._lock:
            self._filename = filename

    def get_filename(self, path: str = '', ext: str = '.parquet') -> str:
        if self._filename is None:
            self.set_filename(f'{datetime.now(timezone.utc).timestamp()}{ext}')
        return f'{path}{self._filename}'
