import logging
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Dict, Tuple, Union, Any, Optional, List

import pyspark
from pyspark.sql import SparkSession
from sortedcontainers import SortedList, SortedDict

from modules.building_block import MediatorKey, Institution, Publication, Article, InteractionType, Utils

# Logger setup
logger = logging.getLogger(__name__)


@dataclass
class Mediator(ABC):
    _instance = None

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock, cls._instance._rlock, cls._instance._wlock = Utils.initiating_rwlock()
            cls._instance._mediator_map: Dict[
                Union[MediatorKey, str], Union[SortedList[Any], SortedDict[int, Article]]] = {}
        return cls._instance

    @property
    def mediator_map(self) -> Dict[Union[MediatorKey, str], Union[SortedList[Any], SortedDict[int, Article]]]:
        with self._rlock:
            return self._mediator_map

    @abstractmethod
    def add_object(self, mediator_key: Union[MediatorKey, str],
                   item: Union[SortedList[Any], SortedDict[int, Article]]) -> None:
        self._mediator_map_interaction(InteractionType.ADD, mediator_key, item)

    def get_object(self, key: Union[MediatorKey, str]) -> Optional[Any]:
        return self._mediator_map_interaction(InteractionType.GET, key)

    def get_nodes_edges(self, spark_session: SparkSession, method_names: List[str], relationship_type: str) -> Tuple[
        pyspark.sql.DataFrame, pyspark.sql.DataFrame]:
        def get_method_attr(obj, method_name) -> Any:
            try:
                with self._rlock:
                    return getattr(obj, method_name, None)
            except AttributeError as e:
                logger.error(f"Error processing key {obj} on {method_name}: {e}")
                return None

        nodes: List[Tuple] = []
        edges: List[Tuple] = []

        with self._rlock:
            for key in self._mediator_map.keys():
                key_method_attr = get_method_attr(key, method_names[0])
                nodes.append((key, type(key), key_method_attr))
                for item in self.get_object(key) or []:
                    item_method_attr = get_method_attr(item, method_names[1])
                    nodes.append((item, type(item), item_method_attr))
                    edges.append((key, type(item), relationship_type))

        nodes_df = spark_session.createDataFrame(nodes, ['id', 'type', 'name'])
        edges_df = spark_session.createDataFrame(edges, ['src', 'dst', 'relationship'])
        return nodes_df, edges_df

    def _mediator_map_interaction(self, interaction: InteractionType, key: Union[MediatorKey, str],
                                  value: Optional[Union[SortedList[Any], SortedDict[int, Article]]] = None) -> Optional[
        Union[SortedList[Any], SortedDict[int, Article]]]:
        if interaction == InteractionType.ADD:
            with self._wlock:
                self._mediator_map[key] = value
        elif interaction == InteractionType.GET:
            with self._rlock:
                return self._mediator_map.get(key)


# Subclass implementations, abbreviated for brevity...

class InstitutionPublicationMediator(Mediator):
    def add_object(self, institution: Institution, publication: Publication, **kwargs) -> None:
        value: SortedList = self.get_object(institution) or SortedList()
        if publication not in value:
            value.add(publication)
            super().add_object(institution, value)

    def get_object(self, institution: Institution) -> Optional[SortedList[Publication]]:
        return super().get_object(institution)


# Other subclasses would follow similar refinements...

class PublishedPrepubArticleMediator(Mediator):
    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._retrieve_initial_prepub_articles = SortedList()
        return cls._instance

    def _remove_doi_from_retrieval_list(self, doi: str) -> None:
        self._prepub_article_list_interaction(InteractionType.REMOVE, doi=doi)

    def _add_doi_to_retrieval_list(self, doi: str) -> None:
        self._prepub_article_list_interaction(InteractionType.ADD, doi=doi)

    def _get_retrieve_initial_prepub_articles(self) -> SortedList[str]:
        return self._prepub_article_list_interaction(InteractionType.GET)

    def _prepub_article_list_interaction(self, interaction: InteractionType, doi: Optional[str] = None) -> SortedList[
        str]:
        if interaction == InteractionType.ADD:
            with self._wlock:
                if doi and doi not in self._retrieve_initial_prepub_articles:
                    self._retrieve_initial_prepub_articles.add(doi)
        elif interaction == InteractionType.REMOVE:
            with self._wlock:
                self._retrieve_initial_prepub_articles.discard(doi)
        with self._rlock:
            return self._retrieve_initial_prepub_articles

    def get_missing_initial_prepub_articles_list(self) -> SortedList[str]:
        return self._get_retrieve_initial_prepub_articles()

    def add_object(self, pub_doi: str, article: Article, **kwargs) -> None:
        article_version_map: Optional[SortedDict[int, Article]] = self.get_object(pub_doi) or SortedDict()
        existing_article = self.get_article_version(pub_doi, article.version)

        if existing_article is None or (
                article.version <= existing_article.version and article.date < existing_article.date):
            article_version_map.update({article.version: article})
            super().add_object(pub_doi, article_version_map)

        first_entry = self.get_first_stored_article_version(pub_doi)
        if article.version == 1:
            self._remove_doi_from_retrieval_list(pub_doi)
        elif first_entry and first_entry.version != 1:
            self._add_doi_to_retrieval_list(pub_doi)

    def get_article_version(self, pub_doi: str, version: int) -> Optional[Article]:
        article_versions = self.get_object(pub_doi)
        return None if article_versions is None else article_versions.get(version)

    def get_first_stored_article_version(self, pub_doi: str) -> Optional[Article]:
        article_versions = self.get_object(pub_doi)
        if article_versions:
            first_version = SortedList(article_versions.keys())[0]
            return self.get_article_version(pub_doi, first_version)

    def convert_pub_doi_to_doi(self, pub_doi: str) -> str:
        first_article = self.get_first_stored_article_version(pub_doi)
        return first_article.doi if first_article else ""


class ArticleLinkTypeMediator:
    pass
