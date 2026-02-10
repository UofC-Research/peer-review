from abc import abstractmethod, ABC
from typing import Tuple, List, Any

import tqdm.contrib.concurrent as tq

from modules.behavioural.database.query import Query, BioRvixQuery


class QueryFactory(ABC):
    """
        An abstract base class for creating and processing queries.

        Methods
        -------
        create_query_list(url: str, json_keys: Tuple[str], col_name: List[str], step: int, total: int) -> List[Query]
            Generates a list of queries based on the provided parameters.
            Parameters:
                url (str): The API endpoint to send the queries to.
                json_keys (Tuple[str]): A tuple of JSON keys to extract from the response.
                col_name (List[str]): Column names for the resulting data.
                step (int): The step size for the query pagination.
                total (int): The total number of items to be queried.
            Returns:
                List[Query]: A list of Query objects based on the provided parameters.

        process_query_list(query_list: List[Query]) -> List[Tuple[int, Query]]
            Processes a list of queries and returns a list of tuples containing status codes and queries.
            Parameters:
                query_list (List[Query]): A list of Query objects to be processed.
            Returns:
                List[Tuple[int, Query]]: A list of tuples where each tuple contains a status code and a Query object.

        get_result_list(results: List[Tuple[int, Query]]) -> List[Any]
            Extracts the results from the processed queries.
            Parameters:
                results (List[Tuple[int, Query]]): A list of tuples where each tuple contains a status code and a Query
                object.
            Returns:
                List[Any]: A list of results extracted from the processed queries.
    """

    @abstractmethod
    def create_query_list(self, url: str, json_keys: Tuple[str], col_name: List[str], step: int, total: int) -> List[
        Query]:
        pass

    @abstractmethod
    def process_query_list(self, query_list: List[Query]) -> List[Tuple[int, Query]]:
        pass

    @abstractmethod
    def get_result_list(self, results: List[Tuple[int, Query]]) -> List[Any]:
        pass


class BioRvixQueryFactory(QueryFactory):
    """
        class BioRvixQueryFactory(QueryFactory, metaclass=Singleton):

        Creates a list of `BioRvixQuery` objects based on the specified URL, keys, column names, step size, and total
        number of items.

        :param: url: The base URL for generating query URLs.
        :param: json_keys: A tuple of string keys to extract data from the JSON response.
        :param: col_name: A list of column names corresponding to the data keys.
        :param: step: The step size for generating pagination.
        :param: total: The total number of items to be paginated.
        :return: A list of `BioRvixQuery` objects.


        Processes a list of `Query` objects by executing them using threading and returns the results.

        :param: query_list: A list of `Query` objects to be processed.
        :return: A list of tuples, where each tuple contains an integer index and a `BioRvixQuery` object.


        Extracts the results from a list of tuples containing query results.

        :param: results: A list of tuples, where each tuple contains an integer index and a `BioRvixQuery` object.
        :return: A list of results extracted from the `BioRvixQuery` objects.
    """

    def create_query_list(self, url: str, json_keys: Tuple[str], col_name: List[str], step: int, total: int) -> List[
        BioRvixQuery]:
        return [BioRvixQuery(url=f'{url}/{cursor}', keys=json_keys, col_names=col_name, page=cursor // step) for cursor
                in range(0, total, step)]

    def process_query_list(self, query_list: List[Query]) -> List[Tuple[int, BioRvixQuery]]:
        return tq.thread_map(lambda p: p.execute(), query_list, desc='BioRvix.execute()', total=len(query_list))

    def get_result_list(self, results: List[Tuple[int, BioRvixQuery]]) -> List[Any]:
        return [y.result for _, y in results]
