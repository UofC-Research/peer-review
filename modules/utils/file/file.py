from io import StringIO
# global variables
from pathlib import Path
from typing import Dict

import numpy as np
from configobj import ConfigObj

from modules.utils.Settings import Settings


def get_dir_list(directory: Path, pattern: str = '') -> np.ndarray:
    """
    :param directory: The directory from which to retrieve the list of files.
    :type directory: `Path`

    :param pattern: Optional. The pattern to use for searching files.
                   Only files matching the pattern will be included in the list.
    :type pattern: `str`, default: ''

    :return: An array of files in the specified directory that match the given pattern (if provided).
    :rtype: `ndarray`
    """
    listing: np.ndarray
    if pattern == '':
        listing = np.array(filter(lambda x: x.is_file(), directory.rglob('*')))
    else:
        listing = np.array(directory.rglob(pattern))

    return listing


def save_stringio(file: Path, iostream: StringIO):
    with open(file, "a") as output_stream:
        output_stream.write(iostream.getvalue())
        output_stream.flush()


def assign_values(config: ConfigObj, params: dict) -> ConfigObj:
    for param in params.keys():
        config[param] = params.get(param)

    return config


def create_config_file(file: str, params: Dict[str, dict], comments: Dict[str, dict]) -> ConfigObj:
    """
    The structure of the comments dictionary is <attribute, <'' or section_name, <keyword , comment>

    the structure of parameter is <'' or section_name, <keyword, value>
    :param file:
    :param params:
    :param comments: a dictionary that contain <command to execute, dictionary of <section, comment> or comments>
    :return:
    """

    config: ConfigObj = ConfigObj()
    config.filename = file
    keywords = params.pop('', None)
    if keywords is not None:
        config = assign_values(config, keywords)

    config = assign_values(config, params)

    config = process_comments(config, comments)
    config.write()

    return config


def read_config_file(file: str) -> Settings:
    return Settings(ConfigObj(file))


def output_comments(config: ConfigObj, attribute: str, key: str, data: dict) -> ConfigObj:
    value = data.get(key)
    if type(data.get(key)) is dict:
        for inner_key in value.keys():
            output_comments(config[key], attribute, inner_key, value)
    else:
        getattr(config, attribute)[key] = value

    return config


def process_comments(config: ConfigObj, comments: dict) -> ConfigObj:
    """
    The structure of the comments dictionary is <attribute, <'' or section_name, [comment or <keyword , comment]>

    :param config:
    :param comments:
    :return:
    """

    for attribute in comments.keys():
        comment_info: Dict[str, dict] = comments.get(attribute)
        keywords = comment_info.pop('', None)
        if keywords is not None:
            for keyword in keywords.keys():
                config = output_comments(config, attribute, keyword, keywords)

        for section in comment_info.keys():
            config = output_comments(config, attribute, section, comment_info)

    return config
