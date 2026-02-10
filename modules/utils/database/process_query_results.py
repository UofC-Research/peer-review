import time
from datetime import datetime
from typing import Any, Dict, List, Tuple, Union

import doi
import numpy as np
import pandas as pd
from pandas import Series
from pandas._libs import NaTType

DATE_FORMAT = '%Y-%m-%d'
DELAY_SECONDS = 60  # extracted constant


class QueryUtils:
    @staticmethod
    def validate_doi(doi_str: str) -> str:
        """
        Validates and returns the given DOI string if it is valid.
        :param doi_str: The input string representing a DOI.
        :return: The validated DOI string.
        :raises ValueError: If the input DOI is invalid.
        """
        doi_str = doi_str.strip()
        if not doi.validate_doi(doi_str):
            raise ValueError(f'Invalid DOI: {doi_str}')
        return doi_str

    @staticmethod
    def get_value(data: Dict[str, Any], key: str) -> Any:
        """
        Retrieve the value associated with the specified key from the dictionary.
        :param data: A dictionary containing key-value pairs.
        :param key: The key whose value needs to be retrieved.
        :return: The value associated with the specified key.
        :raises KeyError: If the key is not found in the dictionary.
        """
        try:
            return data[key]
        except KeyError as e:
            print(f'Key: {key}, Data: {data}\n{e}')
            raise

    @staticmethod
    def parse_date(date_str: str) -> Union[datetime, NaTType]:
        """
        Parses and returns a datetime object from the given date string.
        :param date_str: A string representing a date in 'YYYY-MM-DD' format.
        :return: A datetime object for the parsed date.
        :returns: pd.NaT if the parsing fails.
        """
        date_str = date_str.strip().split(':')[0]
        try:
            return datetime.strptime(date_str, DATE_FORMAT)
        except Exception as e:
            print(e)
            return pd.NaT

    @staticmethod
    def freq_count(df: pd.DataFrame, col_name: str) -> Series:
        """
        Performs frequency count on a specified column of a DataFrame.
        :param df: A pandas DataFrame.
        :param col_name: The column name to perform frequency count on.
        :return: Series representing the frequency count of the specified column.
        """
        return df[col_name].value_counts()

    @staticmethod
    def flatten_list(nested_list: List[List[Any]]) -> List[Any]:
        """
        Flattens and sorts a nested list based on the first element of each sublist.
        :param nested_list: A nested list of elements.
        :return: A flattened and sorted list based on the first element of each sublist.
        """
        return sorted([sublist for inner in nested_list for sublist in inner], key=lambda x: x[0])

    @staticmethod
    def create_df_from_array(data_array: np.ndarray, cols: List[str]) -> pd.DataFrame:
        """
        Creates a DataFrame from a numpy array and list of column names.
        :param data_array: A numpy array containing data.
        :param cols: A list of column names.
        :return: A pandas DataFrame created from the input data.
        """
        return pd.DataFrame(data=data_array[:, 1:], index=data_array[:, 0], columns=cols)

    @staticmethod
    def process_json(json_data: dict, section: str, keys: Tuple[str], offset: int, add_delay: bool = False) -> List[
        List[Any]]:
        """
        Processes and returns data from a specified section of the JSON data.
        :param json_data: A dictionary containing JSON data.
        :param section: The section of JSON data to process.
        :param keys: The keys to extract values from each journal entry.
        :param offset: Value to increment each journal entry index by.
        :param add_delay: Whether to add a delay before processing.
        :return: List of processed journal entry data.
        """
        if add_delay:
            time.sleep(DELAY_SECONDS)
        return [QueryUtils._process_entry(index, entry, keys, offset) for index, entry in
                enumerate(json_data[section])]

    @staticmethod
    def _process_entry(entry_idx: int, journal_entry: Dict[str, Any], keys: Tuple[str], offset: int) -> List[Any]:
        """
        Helper method to process a single journal entry.
        :param entry_idx: The index of the entry.
        :param journal_entry: The journal entry to process.
        :param keys: The keys to extract values from each journal entry.
        :param offset: Value to increment each journal entry index by.
        :return: Processed journal entry data.
        """
        return [entry_idx + offset] + [QueryUtils.get_value(journal_entry, key) for key in keys]


if __name__ == '__main__':
    pass
