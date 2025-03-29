from typing import List, Dict, Union, Optional

from modules.behavioural.database.query import Query
from modules.behavioural.mediator_design_pattern import ArticleLinkTypeMediator
from modules.building_block import Article
from modules.creational.factory_design_pattern import ArticleFactory

"""
Unlike conventional source code comments, the docstring should describe what the function does, not how.

What should a docstring look like?

The doc string line should begin with a capital letter and end with a period.
The first line should be a short description.
If there are more lines in the documentation string, the second line should be blank, visually separating the summary 
from the rest of the description.
The following lines should be one or more paragraphs describing the object’s calling conventions, its side effects, etc.
"""

"""
This is a class for mathematical operations on complex numbers.

Attributes:
    real (int): The real part of complex number.
    imag (int): The imaginary part of complex number.
"""


def get_publication_info(doi: str) -> Dict:
    """
    This method retrieves publication information for a given DOI by using the crossref_commons.retrieval library.
    It returns the publication information as a dictionary.

    :param doi: The DOI (Digital Object Identifier) of the publication.
    :return: A dictionary containing information about the publication.

    Example usage:
    ```
    publication_info = get_publication_info("10.1234/5678")
    print(publication_info)
    ```
    """
    import crossref_commons.retrieval as xref

    import json

    result = xref.get_publication_as_json(doi)
    print(type(result))
    print(json.dumps(result))
    print(result['link'])
    return result


def process_publication_info(doi: str, result: Dict):
    """
    Process publication information based on DOI and result.

    :param doi: A string representing the DOI of the publication.
    :param result: A dictionary containing the result of the publication query.

    :return: None

    """
    # update publication related objects
    article: Optional[Article] = ArticleFactory().get_factory_object(doi)
    # get publication list
    tmp = process_link(result['link'], 'content-type', 'application/xml')
    valid = Query.uri_validator(tmp)
    if tmp is None or valid is False:
        tmp = process_link(result['link'], 'content-type', 'application/pdf')
        if tmp is None or valid is False:
            ArticleLinkTypeMediator().add_object('web', article)
        else:
            # add url to article
            article.publication_link = tmp
            ArticleLinkTypeMediator().add_object('pdf', article)
    else:
        # add url to article
        article.publication_link = tmp
        ArticleLinkTypeMediator().add_object('xml', article)


def process_link(links: List[Dict], key: str, value: str) -> Union[str, None]:
    """
    Processes a list of link dictionaries to find and return a specific URL based
    on a provided key and value match.

    :param links: A list of dictionaries, where each dictionary represents a link
        with various key-value pairs describing its properties.
    :param key: A string representing the key to search for in each dictionary.
    :param value: A string representing the value to match against the specified key.
    :return: A string containing the URL associated with the matching link if found;
        otherwise, returns None.
    """

    for link in links:
        tmp = link.get(key)
        if tmp is None:
            continue
        elif tmp == value:
            return link.get('url')

    return None


'''
for testing
def valid_link(url: str) -> bool:
    from modules.behavioural.database.query import Query

    from requests import HTTPError

    try:
        result = Query.retrieve_web_data(url, 0)
        print(result)
        return True
    except HTTPError:
        return False
'''


if __name__ == '__main__':
    # get_publication_info('10.5555/515151')
    # get_publication_info("10.1101/104778")
    factory = ArticleFactory()
    print(factory().create_base_object(identifier="10.1038/s41598-017-04402-4"))
    get_publication_info("10.1038/s41598-017-04402-4")
    # get_publication_info("10.1109/MM.2019.2910009")
    # valid_link('https://www.nature.com/articles/s41598-017-04402-4.pdf')
    # valid_link('http://xplorestaging.ieee.org/ielx7/40/8709856/08686049.pdf?arnumber=8686049')
