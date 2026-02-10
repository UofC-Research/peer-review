import json
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
import pytest

from modules.behavioural.database.query import Query, BioRvixQuery
from modules.behavioural.mediator_design_pattern import PublishedPrepubArticleMediator
from modules.creational.factory_design_pattern import *
from modules.utils.database.biorxiv_api import BioRvixDatabaseUtils as Bio
from modules.utils.database.process_query_results import QueryUtils


@pytest.fixture()
def query() -> BioRvixQuery:
    """
    Returns an instance of the Query class initialized with a specific URL, keys, and column names.

    :return: An instance of the Query class.
    """

    url = 'https://api.biorxiv.org/details/medrxiv/10.1101/2021.04.29.21256344'
    keys: Tuple = ('doi', 'title', 'authors', 'author_corresponding', 'author_corresponding_institution', 'date',
                   'version', 'type', 'category', 'jatsxml', 'published')
    col_names: List = ["DOI", "Title", "Authors", "Corresponding_Authors", "Institution", "Date", "Version", "Type",
                       "Category", "Xml", "Published"]
    query = BioRvixQuery(url, keys, col_names)

    return query


@pytest.fixture()
def prepub_query(query: BioRvixQuery) -> BioRvixQuery:
    """
    Executes a query to retrieve prepublication data from the BioRxiv API.

    :return: A dictionary containing the prepublication data.
    """

    # url = 'https://api.biorxiv.org/pubs/medrxiv/10.1101/2021.04.29.21256344'
    # url = 'https://api.biorxiv.org/details/biorxiv/10.1101/339747'
    # url = 'https://api.biorxiv.org/details/medrxiv/10.1101/2021.04.29.21256344'
    return query.fetch_json_data(attempts=0)[1]


@pytest.fixture()
def pubs_query() -> BioRvixQuery:
    url: str = 'https://api.biorxiv.org/pubs/medrxiv/10.1101/2021.04.29.21256344'
    keys: Tuple = (
        "preprint_doi", "published_doi", "preprint_title", "preprint_authors", "preprint_author_corresponding",
        "preprint_author_corresponding_institution", "preprint_category", "published_journal", "preprint_date",
        "published_date")
    col_names: List = ["DOI", "pub_DOI", "Title", "Authors", "Corresponding_Authors", "Institution", "Category",
                       "Journal", "Preprint_Date", "Published_Date"]

    return BioRvixQuery(url, keys, col_names)


@pytest.fixture()
def pub_query(pubs_query: BioRvixQuery) -> Union[BioRvixQuery, Any]:
    """
    Retrieve publication data from the BioRxiv API.

    :return: The publication data, specifically the journal name.
    """

    # url = 'https://api.biorxiv.org/pubs/medrxiv/10.1101/2021.04.29.21256344'
    # keys: Tuple = ('published_journal',)
    # col_names: List[str] = ['Journal']
    # query: Query = Query(url, keys, col_names)

    return pubs_query.fetch_json_data(attempts=0)[1]


@pytest.fixture
def prepub_test_file():
    """
    This uses the pytest.fixture feature to reduce code smells so that the loading and processing of test data
    is modularized to reduce the chance of bugs.

    :return: the data is formatted into a tabular format with the use of numpy arrays.
    """
    keys: tuple = ('doi', 'title', 'authors', 'author_corresponding', 'author_corresponding_institution', 'date',
                   'version', 'type', 'category', 'jatsxml', 'published')
    filename = Path('../../data/prepub-test.json').absolute()
    assert filename.exists()
    json_data = json.load(filename.open())
    result = np.array(QueryUtils.process_json(json_data, 'collection', keys, 0))

    return result


def load_articles(df: pd.DataFrame):
    for row in range(len(df)):
        Bio.create_article(doi=df.loc[str(row), 'DOI'],
                           title=df.loc[str(row), 'Title'],
                           authors=df.loc[str(row), 'Authors'],
                           corr_authors=df.loc[str(row), 'Corresponding_Authors'],
                           institution=df.loc[str(row), 'Institution'],
                           date=df.loc[str(row), 'Date'],
                           version=df.loc[str(row), 'Version'],
                           type=df.loc[str(row), 'Type'],
                           category=df.loc[str(row), 'Category'],
                           xml=df.loc[str(row), 'Xml'],
                           pub_doi=df.loc[str(row), 'Published'])


def load_article_factory_dataframe(result: np.ndarray,
                                   col_names=("DOI", "Title", "Authors", "Corresponding_Authors", "Institution", "Date",
                                              "Version", "Type",
                                              "Category", "Xml", "Published")) -> pd.DataFrame:
    df: pd.DataFrame = Bio.create_prepublish_df(QueryUtils.create_df_from_array(data_array=result, cols=col_names))
    load_articles(df)
    return df


def test_instantiation_base_object():
    with pytest.raises(RuntimeError, match='Please instantiate class through the corresponding Factory'):
        Article()
        Journal()
        Publication()
        Department()
        Institution()
        Category()


def test_singleton_design_pattern():
    assert ArticleFactory() is ArticleFactory()
    assert ArticleFactory() is not None
    assert JournalFactory() is JournalFactory()
    assert JournalFactory() is not None
    assert AuthorFactory() is AuthorFactory()
    assert ArticleFactory() is not None
    assert PublicationFactory() is PublicationFactory()
    assert PublicationFactory() is not None
    assert DepartmentFactory() is DepartmentFactory()
    assert DepartmentFactory() is not None
    assert InstitutionFactory() is InstitutionFactory()
    assert InstitutionFactory() is not None
    assert CategoryFactory() is CategoryFactory()
    assert CategoryFactory() is not None

    assert ArticleFactory()._rlock is not None
    assert ArticleFactory()._wlock is not None


def test_create_article(prepub_query):
    """
    :param prepub_test_file: The file containing the prepublication test data in the form of a numpy array.
    :return: None

    This method is used to test the `create_article` function. It takes a `prepub_test_file` parameter which should be
    a numpy array. The method loads the prepublication test data from the `prepub_test_file` using
    `load_article_factory_dataframe` function. It then iterates through each row in the loaded dataframe.

    For each row, it retrieves the values for the `DOI`, `Title`, `Authors`, `Corresponding_Authors`, `Institution`,
    `Date`, `Version`, `Type`, `Category`, `Xml`, `Published` columns and passes them as arguments to the
    `create_article` function.

    After creating the article, it verifies that the `DOI` generated matches the expected value
    '10.1101/001768' using an assertion. It also checks if the article object is successfully created by
    calling `ArticleFactory().get_base_object` with `identifier` parameter as `doi` and asserts that it is not `None`.

    Note: In order to use this method, make sure to import `np` from `numpy` and `pd` from `pandas` libraries.
    """

    result = np.array(QueryUtils.process_json(prepub_query.result, 'collection', prepub_query.keys, 0))
    df = Bio.create_prepublish_df(QueryUtils.create_df_from_array(result, prepub_query.col_names))
    for row in range(len(df)):
        row = str(row)
        doi = df.loc[row, 'DOI']
        Bio.create_article(doi=df.loc[row, 'DOI'], title=df.loc[row, 'Title'],
                           authors=df.loc[row, 'Authors'], corr_authors=df.loc[row, 'Corresponding_Authors'],
                           institution=df.loc[row, 'Institution'], date=df.loc[row, 'Date'],
                           version=df.loc[row, 'Version'], type=df.loc[row, 'Type'],
                           category=df.loc[row, 'Category'], xml=df.loc[row, 'Xml'],
                           pub_doi=df.loc[row, 'Published'])

        assert doi == '10.1101/2021.04.29.21256344'
        assert ArticleFactory().get_factory_object(identifier=doi) is not None


def test_create_journal(pubs_query: Query) -> None:
    """
    The function test_create_journal is a test function which takes in one argument, pubs_query, a Query object
    representing a query used to retrieve journal information from the BioRxiv database.

    :param pubs_query: A Query object representing the query used to retrieve journal information from a database.
    :return: None
    """

    journal = Bio.create_journal(name=Bio.get_journal_name(pubs_query))
    assert Bio.get_journal_name(pubs_query) == 'PLOS ONE'
    assert type(journal) is Journal
    assert journal is JournalFactory().get_factory_object(journal.title)
    assert journal.prefix == ''
    assert journal.issn == ''
    assert journal.impact_factor == 0.0


def test_create_publication(prepub_query: Query, pubs_query: Query) -> None:
    """
    :param prepub_query: A Query object representing the prepublication data.
    :param pubs_query: A query representing the publication data.
    :return: The created Publication object.

    This method takes a prepublication query and a publication query as input. It processes the prepublication query to
    obtain a result, creates a prepublication DataFrame, and then creates
    * an Article object using the data from the DataFrame. The Article object is then used to create a Journal object
      and a Publication object. The method asserts that the created Article and Publication objects are not None.

    Example usage:
    prepub_query = Query(...)
    pubs_query = ...
    result = test_create_publication(prepub_query, pubs_query)
    """

    result = np.array(QueryUtils.process_json(prepub_query.result, 'collection', prepub_query.keys, 0))
    df = Bio.create_prepublish_df(QueryUtils.create_df_from_array(data_array=result, cols=prepub_query.col_names))
    article = Bio.create_article(doi=df.loc['0', 'DOI'],
                                 title=df.loc['0', 'Title'],
                                 authors=df.loc['0', 'Authors'],
                                 corr_authors=df.loc['0', 'Corresponding_Authors'],
                                 institution=df.loc['0', 'Institution'],
                                 date=df.loc['0', 'Date'],
                                 version=df.loc['0', 'Version'],
                                 type=df.loc['0', 'Type'],
                                 category=df.loc['0', 'Category'],
                                 xml=df.loc['0', 'Xml'],
                                 pub_doi=df.loc['0', 'Published'])

    assert article is not None
    journal = Bio.create_journal(name=Bio.get_journal_name(pubs_query))
    publication = Bio.create_publication(journal=journal, article=article)
    assert publication is PublicationFactory().get_factory_object(article.pub_doi)


def test_receive_initial_version(prepub_test_file: np.ndarray, prepub_query: Query) -> None:
    """
    Test method to receive the initial version of articles.

    :param prepub_test_file: The file containing the prepublication data.
    :param prepub_query: The query object containing column names.
    :return: None
    """

    df: pd.DataFrame = Bio.create_prepublish_df(
        QueryUtils.create_df_from_array(data_array=prepub_test_file, cols=prepub_query.col_names))
    load_articles(df)
    missing_items: SortedList[str] = PublishedPrepubArticleMediator().get_missing_initial_prepub_articles_list()
    url = 'https://api.biorxiv.org/details/biorxiv/'
    articles: List[Article] = []
    for missing in missing_items:
        doi = PublishedPrepubArticleMediator().convert_pub_doi_to_doi(missing)
        query = BioRvixQuery(url + doi, prepub_query.keys, prepub_query.col_names)
        result: BioRvixQuery = query.execute(0)[1]
        data: dict = result.result
        tmp: np.array = np.array(QueryUtils.process_json(data, 'collection', prepub_query.keys, 0))
        df = Bio.create_prepublish_df(QueryUtils.create_df_from_array(data_array=tmp, cols=prepub_query.col_names))
        for line in range(len(df)):
            line = str(line)
            articles.append(Bio.create_article(doi=df.loc[line, 'DOI'], title=df.loc[line, 'Title'],
                                               authors=df.loc[line, 'Authors'],
                                               corr_authors=df.loc[line, 'Corresponding_Authors'],
                                               institution=df.loc[line, 'Institution'], date=df.loc[line, 'Date'],
                                               version=df.loc[line, 'Version'], type=df.loc[line, 'Type'],
                                               category=df.loc[line, 'Category'], xml=df.loc[line, 'Xml'],
                                               pub_doi=df.loc[line, 'Published']))

        pub_doi: str = articles[0].pub_doi
        article = PublishedPrepubArticleMediator().get_object(pub_doi)[1]
        assert article.version == 1


def test_add_publication_list(prepub_test_file):
    ArticleFactory._pub_list = set()
    df: pd.DataFrame = load_article_factory_dataframe(prepub_test_file)
    assert sorted(list(set(df[df.Published.apply(lambda x: x.upper()) != 'NA'].Published))) == \
           sorted(ArticleFactory().publication_list)
