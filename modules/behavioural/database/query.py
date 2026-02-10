import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, List, Any
from urllib.parse import urlparse

import requests
from readerwriterlock import rwlock
from requests import HTTPError, Response

MAX_ATTEMPTS: int = 10
SLEEP_INTERVAL: int = 300
VALID_ATTRIBUTES: Tuple[str, str, str] = ('text', 'content', 'json')


@dataclass
class Query(ABC):
    """
    Represents an abstract base class for executing queries and retrieving web data.

    This class provides shared functionality for handling URLs, validating URI structure,
    retrieving web data with retries and exponential backoff, and accessing response content
    using specific attributes. Subclasses must implement the `execute` method for executing
    specific queries.

    :ivar MAX_ATTEMPTS: The maximum number of retry attempts for web requests.
    :type MAX_ATTEMPTS: int
    :ivar SLEEP_INTERVAL: The base interval in seconds for exponential backoff during retries.
    :type SLEEP_INTERVAL: int
    :ivar VALID_ATTRIBUTES: A tuple of valid response content attributes for retrieval.
    :type VALID_ATTRIBUTES: Tuple[str]
    """

    MAX_ATTEMPTS: int = 10
    SLEEP_INTERVAL: int = 300
    VALID_ATTRIBUTES: Tuple[str] = ('text', 'content', 'json')

    @property
    def result(self) -> Any:
        with self._rlock:
            return self._result

    @property
    def keys(self) -> Tuple[str]:
        with self._rlock:
            return self._keys

    @property
    def url(self) -> str:
        with self._rlock:
            return self._url

    @property
    def col_names(self) -> List[str]:
        with self._rlock:
            return self._col_names

    def __init__(self, url: str, keys: Tuple[str], col_names: List[str], result: Any = None, *args, **kwargs):
        """
        Represents an object that initializes certain attributes and creates a fair read-write lock.
        This class is designed to handle URL validation, key storage, column storage, and optionally
        store some result value while maintaining thread safety using read-write locks.

        :param url: The URL to validate and store. If the URL is invalid, an empty string is stored.
        :type url: str
        :param keys: A tuple of keys to be used/stored.
        :type keys: Tuple[str]
        :param col_names: A list of column names to be used/stored.
        :type col_names: List[str]
        :param result: An optional argument to store any result-related data. Defaults to None.
        :type result: Any
        :param args: Variable-length positional arguments for further extensions or subclassing.
        :type args: tuple
        :param kwargs: Variable-length keyword arguments for further extensions or subclassing.
        :type kwargs: dict
        """

        self._lock = rwlock.RWLockFair()
        self._rlock = self._lock.gen_rlock()
        self._wlock = self._lock.gen_wlock()
        self._url = url if Query.uri_validator(url) else ''
        self._keys = keys
        self._col_names = col_names
        self._result = result

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Abstract method to be implemented by subclasses. This method defines a contract that
        all derived classes must adhere to. It is intended to perform a specific execution
        logic as determined by the derived class implementation.

        :param args: Positional arguments required for execution. The exact use and
            expected content of these will depend on the implementation in
            the subclass.
        :param kwargs: Keyword arguments required for execution. The exact use and
            expected content of these will also depend on the implementation
            in the subclass.
        :return: The result of the execution. The type of the result will be dependent
            on the implementation of the derived class.
        """
        pass

    @staticmethod
    def retrieve_web_data(url: str, attempts: int = 0, attribute: str = "text") -> Any:
        """
        Retrieve content from the web based on the provided URL and specified attribute.

        This static method performs an HTTP request to the given URL and extracts the
        requested content type from the response. If the specified attribute is not
        valid, it raises a ValueError. The number of request attempts can be adjusted
        through the `attempts` parameter. The method relies on private methods of the
        `Query` class to make the HTTP request and extract the desired content.

        :param url: The URL of the web resource to be retrieved.
        :param attempts: The number of retry attempts for the HTTP request. Defaults to 0.
        :param attribute: The content type to extract from the HTTP response (e.g., "text").
        :return: The extracted content from the web response as specified by the attribute.
        """

        attribute = attribute.strip().lower()
        if attribute not in VALID_ATTRIBUTES:
            raise ValueError(f'Invalid attribute: {attribute}. Expected one of {VALID_ATTRIBUTES}')

        response = Query._make_request(attempts, url)
        return Query._get_response_content(response, attribute)

    @staticmethod
    def _get_response_content(response: Response, attribute: str) -> Any:
        """
        Extracts the content from a response object based on the specified attribute. The method
        uses the attribute name to dynamically fetch the corresponding method or value from
        the response object. If the attribute is 'json', it calls the appropriate method. If
        a TypeError occurs during the process, it safely returns None without raising an
        exception. This provides flexibility in handling response objects without forcing
        strict adherence to predefined access methods.

        :param response: The response object from which content is to be extracted. Must
            support dynamic attribute access for the specified `attribute`.
        :type response: Response
        :param attribute: The name of the attribute or method to be used for extracting
            the content from the response object. For example, 'json', 'text',
            etc.
        :type attribute: str
        :return: Extracted content from the response object corresponding to the provided
            attribute, or None if a TypeError is encountered.
        :rtype: Any
        """
        try:
            response_func = getattr(response, attribute)
            return response_func() if attribute == 'json' else response_func
        except TypeError:
            return None

    @staticmethod
    def _make_request(attempts: int, url: str) -> Response:
        """
        Makes an HTTP GET request to the provided URL and manages retries based on HTTP errors
        with specific status codes.

        The method uses exponential backoff to retry the operation in case of specific transient
        errors that are listed in the `retry_list`. If the number of attempts exceeds the maximum
        allowed retries, the method raises an `HTTPError`. Otherwise, it returns the HTTP response.

        :param attempts: The current attempt number, used for managing the number of retries.
        :type attempts: int
        :param url: The URL to make the GET request to.
        :type url: str
        :return: The HTTP response object obtained from the GET request.
        :rtype: Response
        :raises HTTPError: If a non-retryable error status code is encountered or the number of
            attempts exceeds the maximum limit.
        """
        retry_list = {requests.codes['reset'], requests.codes['partial'], requests.codes['im_used'],
                      requests.codes['timeout'], requests.codes['too_many'], requests.codes['none'],
                      requests.codes['bandwidth']}
        try:
            response: Response = requests.get(url)
            response.raise_for_status()
            return response
        except HTTPError as e:
            if e.response.status_code in retry_list:
                if attempts >= MAX_ATTEMPTS:
                    raise HTTPError from e
                wait_time = SLEEP_INTERVAL * (2 ** attempts)  # Exponential backoff
                time.sleep(wait_time)
                return Query._make_request(attempts + 1, url)
            else:
                raise HTTPError from e

    @staticmethod
    def uri_validator(x: str) -> bool:
        try:
            result = urlparse(x)
            return all([result.scheme, result.netloc])
        except AttributeError:
            return False


@dataclass
class BioRvixQuery(Query):
    """
    Handles querying and retrieving data from the BioRvix data source.

    This class is designed to facilitate interaction with the BioRvix REST API,
    allowing retrieval of JSON data based on specified parameters. It maintains
    state regarding the current page of results being queried.

    :ivar _page: Tracks the current page number for the query.
    :type _page: int
    """

    _page: int = 0

    @property
    def page_number(self) -> int:
        with self._rlock:
            return self._page

    def __init__(self, url: str, keys: Tuple[str], col_names: List[str], page: int = 0):
        super().__init__(url, keys, col_names, None)
        with self._wlock:
            self._page = page

    def get_total_entries(self) -> int:
        json_info = self.retrieve_web_data(self.url.rstrip('/') + '/0', attribute='json')
        return int(json_info["messages"][0]["total"])

    def fetch_json_data(self, attempts: int = 0) -> Tuple[int, 'BioRvixQuery']:
        json_data = self.retrieve_web_data(self.url, attempts=attempts, attribute="json")
        with self._wlock:
            self._result = json_data
        return self.page_number, self

    def execute(self, attempts: int = 0) -> Tuple[int, 'BioRvixQuery']:
        return self.fetch_json_data(attempts)
