from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any, Tuple

from readerwriterlock import rwlock


class NoDefaultValueGiven(Exception):
    pass


@dataclass
class BaseObject(ABC):
    """
    Class BaseObject

    Abstract base class for building blocks.

    Methods:
    - not_empty(*args, **kwargs) -> bool
        Check if the class is instantiated correctly.
        Parameters:
            *args: positional arguments
            **kwargs: keyword arguments
        Returns:
            bool: True if the class is instantiated correctly, False otherwise
        Raises:
            RuntimeError: If the class is not instantiated through the corresponding Factory

    - get_value(key: Any, default: Any = NoDefaultValueGiven, **kwargs) -> Any
        Get the value of a key from keyword arguments or return the default value.
        Parameters:
            key (Any): The key to lookup in the keyword arguments
            default (Any): Default value to return if the key is not found (optional)
            **kwargs: Keyword arguments
        Returns:
            Any: The value associated with the key, or the default value if the key is not found
        Raises:
            NoDefaultValueGiven: If no value was assigned to the key

    - _setattr(obj: object, fields: List[str], default: Any = NoDefaultValueGiven, **kwargs)
        Set attributes on an object using the provided fields and values from keyword arguments.
        Parameters:
            obj (object): The object to set attributes on
            fields (List[str]): List of attribute names to set on the object
            default (Any): Default value to use if a field is not found in keyword arguments (optional)
            **kwargs: Keyword arguments containing field-value pairs

    """

    def __init__(self, *args, **kwargs) -> None:
        if args == () and kwargs == {}:
            raise RuntimeError('Please instantiate class through the corresponding Factory')

        self._lock, self._rlock, self._wlock = Utils.initiating_rwlock()

    @staticmethod
    def get_value(key: Any, default: Any = NoDefaultValueGiven, **kwargs) -> Any:
        """
        Returns the value associated with the given key from kwargs.

        :param key: The key to lookup in kwargs.
        :param default: The default value to return if the key is not found in kwargs. Defaults to NoDefaultValueGiven.
        :param kwargs: The keyword arguments from which to lookup the value.
        :return: The value associated with the key, or the default value if not found.
        :raises NoDefaultValueGiven: If the key is not found and no default value was provided.
        """
        result = kwargs.get(key, default)
        if isinstance(result, NoDefaultValueGiven):
            raise NoDefaultValueGiven(f'No value was assigned to {key}:')

        return result

    @staticmethod
    def _setattr(obj: 'BaseObject', fields: List[str], default: Any = NoDefaultValueGiven, **kwargs):
        """
        Sets the attributes of an object with the given fields.

        :param obj: The object whose attributes need to be set.
        :param fields: A list of strings specifying the names of the fields to be set.
        :param default: The default value to be used if a field is not found in kwargs. Defaults to NoDefaultValueGiven.
        :param kwargs: Additional keyword arguments that will be used to set the field values.
        :return: None
        """
        with obj._wlock:
            for field in fields:
                setattr(obj, f"_{field}", BaseObject.get_value(field, default, **kwargs))


class MediatorKey(ABC):
    pass


@dataclass
class Department(MediatorKey, BaseObject):
    def __init__(self, *args, **kwargs):
        """
        Initialize the object.

        :param args: (optional) Variable-length argument list.
        :param kwargs: (optional) Keyword arguments.

        """
        super().__init__(*args, **kwargs)


@dataclass
class Institution(MediatorKey, BaseObject):
    def __init__(self, *args, **kwargs):
        """
        Initialize the object.

        :param args: (optional) Variable-length argument list.
        :param kwargs: (optional) Keyword arguments.

        """
        super().__init__(*args, **kwargs)


@dataclass
class Category(MediatorKey, BaseObject):
    def __init__(self, *args, **kwargs):
        """
        Initialize the object.

        :param args: (optional) Variable-length argument list.
        :param kwargs: (optional) Keyword arguments.

        """
        super().__init__(*args, **kwargs)


@dataclass
class Author(BaseObject):
    def __init__(*args, **kwargs):
        """
        Initialize the object.

        :param args: (optional) Variable-length argument list.
        :param kwargs: (optional) Keyword arguments.

        """
        super().__init__(*args, **kwargs)


@dataclass
class Article(BaseObject):
    """

    Article Class
    -------------

    This class represents an article and inherits from the `BaseObject` base class.

    Attributes:
    -----------
    - `_doi` (str): The DOI (Digital Object Identifier) of the article.
    - `_title` (str): The title of the article.
    - `_authors` (str): The authors of the article. This should be a string representing a list of `Author` object(s).
    - `_corr_authors` (str): The corresponding authors of the article. This should be a string representing a list of
                             `Author` object(s).
    - `_institution` (str): The institution associated with the article. This should be an `Institution` object.
    - `_date` (datetime): The date of the article.
    - `_version` (int): The version of the article.
    - `_type` (str): The type of the article, e.g. "new result", "contradictory results", etc.
    - `_category` (List[str]): The subject category(ies) of the article.
    - `_xml` (str): The XML representation of the article.
    - `_pub_doi` (str): The DOI of the publication.

    Optional attributes:
    -------------------
    - `_corr_authors_detail` (Optional[Author]): Additional details of the corresponding authors. To be removed when
                                                 `Author` class is defined.
    - `_authors_detail` (Optional[List[Author]]): Additional details of the authors. To be removed when `Author` class
                                                  is defined.
    - `_publication_link` (Optional[str]): The publication link of the article.

    Methods:
    --------
    - `__init__(*args, **kwargs)`: Initializes the `Article` object with the given arguments and keyword arguments.
    - `title() -> str`: Returns the title of the article.
    - `doi() -> str`: Returns the DOI of the article.
    - `publication_link() -> str`: Returns the publication link of the article.
    - `publication_link(link: str)`: Sets the publication link of the article.
    - `version() -> int`: Returns the version of the article.
    - `date() -> datetime`: Returns the date of the article.
    - `pub_doi() -> str`: Returns the publication DOI of the article.

    Note: Please note that the format of the attributes and methods may need to be adjusted based on the desired style
          guidelines.

    """

    _doi: str
    _title: str
    _authors: str  # todo: should be a list of Author object(s)
    _corr_authors: str  # todo: should be a list of Author object(s)
    _institution: str  # todo: should be an Institution object
    _date: datetime
    _version: int
    _type: str  # some preprint database assign the type of article it is e.g. new result, contradictory results ...
    _category: List[str]  # article's subject
    _xml: str
    _pub_doi: str
    _corr_authors_detail: Optional[Author]  # todo: remove when Author class has been defined
    _authors_detail: Optional[List[Author]]  # todo: remove when Author class has been defined
    _publication_link: Optional[str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # fields that should have a value when the Article class is instantiated
        fields = ['doi', 'title', 'authors', 'corr_authors', 'institution', 'date', 'version', 'type', 'category',
                  'xml', 'pub_doi']
        super()._setattr(self, fields, **kwargs)
        # fields that may not have a value when the Article class is instantiated
        fields = ['authors_detail', 'corr_authors_detail', 'publication_link']
        super()._setattr(self, fields, None, **kwargs)

    @property
    def title(self) -> str:
        return self._title

    @property
    def doi(self) -> str:
        return self._doi

    @property
    def publication_link(self) -> str:
        return self._publication_link

    @publication_link.setter
    def publication_link(self, link: str):
        self._publication_link = link

    @property
    def version(self) -> int:
        return self._version

    @property
    def date(self) -> datetime:
        return self._date

    @property
    def pub_doi(self) -> str:
        return self._pub_doi

    @property
    def category(self) -> List[str]:
        return self._category

    @property
    def type(self) -> str:
        return self._type


@dataclass
class Journal(BaseObject):
    """
    Initialize the Journal object with the given parameters.

    :param prefix: A string representing the prefix of the journal (optional).
    :param title: A string representing the title of the journal.
    :param issn: A string representing the ISSN of the journal (optional).
    :param impact_factor: A float representing the impact factor of the journal (optional).
    """
    _prefix: Optional[str]
    _issn: Optional[str]
    _impact_factor: Optional[float]
    _title: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super()._setattr(self, ['title'], **kwargs)
        super()._setattr(self, ['prefix', 'issn'], '', **kwargs)
        super()._setattr(self, ['impact_factor'], 0.0, **kwargs)

    @property
    def impact_factor(self) -> float:
        return self._impact_factor

    @impact_factor.setter
    def impact_factor(self, journal_impact_factor: float):
        self._impact_factor = journal_impact_factor

    @property
    def title(self) -> str:
        return self._title

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, prefix: str) -> None:
        self._prefix = prefix

    @property
    def issn(self) -> str:
        return self._issn

    @issn.setter
    def issn(self, issn: str) -> None:
        self._issn = issn


class Publication(BaseObject):
    _journal: Journal
    _article: Article
    _name: str
    _pub_doi: str

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        super()._setattr(self, ['journal', 'article'], **kwargs)
        article = self._article
        self._name = f'{article.title}\n{article.pub_doi}'
        self._pub_doi = article.pub_doi

    @property
    def article(self) -> Article:
        return self._article

    @article.setter
    def article(self, article: Article) -> None:
        self._article = article

    @property
    def journal(self) -> Journal:
        return self._journal

    @journal.setter
    def journal(self, journal: Journal) -> None:
        self._journal = journal


class InteractionType(Enum):
    REMOVE = 1
    ADD = 2
    UPDATE = 3
    GET = 4


class Utils:
    @staticmethod
    def initiating_rwlock() -> Tuple[rwlock.RWLockFair, object, object]:
        lock = rwlock.RWLockFair()
        rlock = lock.gen_rlock()
        wlock = lock.gen_wlock()

        return lock, rlock, wlock
