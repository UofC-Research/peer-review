from typing import Optional

import pytest

from modules.behavioural.mediator_design_pattern import PublishedPrepubArticleMediator
from modules.building_block import Article
from modules.creational.factory_design_pattern import ArticleFactory
from modules.utils.database.process_query_results import QueryUtils
from tests.creational.test_factory_design_pattern import load_article_factory_dataframe


def test_singleton():
    mediator1 = PublishedPrepubArticleMediator()
    mediator2 = PublishedPrepubArticleMediator()
    assert mediator1 == mediator2
    assert mediator1 is not None
    assert mediator1._lock == mediator2._lock
    assert mediator1._lock is not None


def test_published_prepub_mediator(prepub_test_file):
    load_article_factory_dataframe(prepub_test_file)
    test_doi = '10.7554/eLife.72498'
    article: Optional[Article] = PublishedPrepubArticleMediator().get_first_stored_article_version(test_doi)
    assert PublishedPrepubArticleMediator() == PublishedPrepubArticleMediator()
    assert PublishedPrepubArticleMediator is not None
    assert article is not None
    expected: Optional[Article] = ArticleFactory().get_factory_object(article.doi)
    assert article.doi == expected.doi
    assert article.version == expected.version


def test_get_first_stored_article_version(prepub_test_file):
    assert prepub_test_file.shape == (100, 12)
    load_article_factory_dataframe(prepub_test_file)
    test_doi = '10.7554/eLife.72498'
    article: Article = PublishedPrepubArticleMediator().get_first_stored_article_version(test_doi)
    assert article.version == 4
    assert test_doi in PublishedPrepubArticleMediator().get_missing_initial_prepub_articles_list()


def test_complete_article_info(completed_test_file):
    test_doi = '10.1155/2022/3248731'
    assert (PublishedPrepubArticleMediator().get_first_stored_article_version(test_doi) is not None) == True
    assert (test_doi in PublishedPrepubArticleMediator().get_missing_initial_prepub_articles_list()) == True
    assert completed_test_file.shape == (5, 12)
    load_article_factory_dataframe(completed_test_file)
    article: Article = PublishedPrepubArticleMediator().get_first_stored_article_version(test_doi)
    assert article.version == 1
    assert test_doi not in PublishedPrepubArticleMediator().get_missing_initial_prepub_articles_list()


@pytest.fixture
def prepub_test_file():
    from pathlib import Path
    import json

    keys: tuple = ('doi', 'title', 'authors', 'author_corresponding', 'author_corresponding_institution', 'date',
                   'version', 'type', 'category', 'jatsxml', 'published')
    filename = '../../data/prepub-test.json'
    assert Path(filename).exists()

    json_data = json.load(Path(filename).open())
    import numpy as np
    result = np.array(QueryUtils.process_json(json_data, 'collection', keys, 0))

    return result


@pytest.fixture
def completed_test_file():
    from pathlib import Path
    import json

    #    keys: tuple = ('doi', 'title', 'authors', 'author_corresponding', 'author_corresponding_institution', 'date',
    #                   'version', 'type', 'license', 'category', 'jatsxml', 'abstract', 'published', 'server')
    keys: tuple = ('doi', 'title', 'authors', 'author_corresponding', 'author_corresponding_institution', 'date',
                   'version', 'type', 'category', 'jatsxml', 'published')
    filename = '../../data/completed-test.json'
    assert Path(filename).exists()

    json_data = json.load(Path(filename).open())
    import numpy as np
    result = np.array(QueryUtils.process_json(json_data, 'collection', keys, 0))

    return result
