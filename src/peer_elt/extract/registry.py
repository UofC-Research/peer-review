from __future__ import annotations

"""Registry framework for preprint server clients and extraction.

This module provides a small abstraction layer for preprint metadata extraction:

- :class:`PreprintServerClient` defines the client contract for a single server.
- :class:`PreprintServerRegistry` stores clients keyed by server slug.
- :func:`default_registry` returns a registry seeded with built-in clients.
- :class:`RegistryExtractor` adapts the registry to the pipeline
  :class:`peer_elt.interfaces.Extractor` interface.

The intent is to keep server-specific API details in client implementations
while allowing the pipeline to select a server by configuration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Iterable, List

import pandas as pd

from peer_elt.config import RetryConfig, SourceConfig
from peer_elt.interfaces import Extractor


class PreprintServerClient(ABC):
    """Abstract client interface for pulling metadata from a preprint server.

    Implementations are expected to be configured for a single server slug
    (e.g., ``"biorxiv"``) and to return raw metadata as a DataFrame.

    Attributes
    ----------
    server : str
        Server slug that this client supports.
    """

    server: str

    @abstractmethod
    def fetch(
        self,
        date_from: str,
        date_to: str,
        retry_config: RetryConfig,
    ) -> pd.DataFrame:
        """Fetch raw metadata for a date window.

        Parameters
        ----------
        date_from : str
            Inclusive start date in ``YYYY-MM-DD`` format.
        date_to : str
            Inclusive end date in ``YYYY-MM-DD`` format.
        retry_config : peer_elt.config.RetryConfig
            Retry/backoff configuration for external API calls.

        Returns
        -------
        pandas.DataFrame
            Raw metadata for the configured server and date window.

        Raises
        ------
        NotImplementedError
            Always raised by the abstract base class.
        """
        raise NotImplementedError


class PreprintServerRegistry:
    """Registry for available preprint server clients.

    The registry maps server slugs (strings) to concrete
    :class:`PreprintServerClient` instances and provides helper methods for
    validation and lookup.
    """

    def __init__(self) -> None:
        self._clients: Dict[str, PreprintServerClient] = {}

    def register(self, client: PreprintServerClient) -> None:
        """Register a client for its server slug.

        Parameters
        ----------
        client : PreprintServerClient
            Client instance to register. The client is stored under
            ``client.server``.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If a client is already registered for ``client.server``.
        """
        if client.server in self._clients:
            raise ValueError(f"Client already registered for server: {client.server}")
        self._clients[client.server] = client

    def has_server(self, server: str) -> bool:
        """Return True if a client is registered for the given server slug.

        Parameters
        ----------
        server : str
            Server slug to check.

        Returns
        -------
        bool
            True if the server is registered, otherwise False.
        """
        return server in self._clients

    def get(self, server: str) -> PreprintServerClient:
        """Return the client registered for a server slug.

        Parameters
        ----------
        server : str
            Server slug to look up.

        Returns
        -------
        PreprintServerClient
            Client registered for the requested server.

        Raises
        ------
        ValueError
            If no client is registered for the given server slug.
        """
        try:
            return self._clients[server]
        except KeyError as exc:
            raise ValueError(f"Unsupported source server: {server}") from exc

    def supported_servers(self) -> List[str]:
        """Return supported server slugs in sorted order.

        Returns
        -------
        list[str]
            Sorted list of registered server slugs.
        """
        return sorted(self._clients.keys())

    def register_all(self, clients: Iterable[PreprintServerClient]) -> None:
        """Register multiple clients.

        Parameters
        ----------
        clients : Iterable[PreprintServerClient]
            Client instances to register.

        Returns
        -------
        None
        """
        for client in clients:
            self.register(client)

    @classmethod
    def from_clients(cls, clients: Iterable[PreprintServerClient]) -> "PreprintServerRegistry":
        """Construct a registry and register the provided clients.

        Parameters
        ----------
        clients : Iterable[PreprintServerClient]
            Clients to register in the new registry.

        Returns
        -------
        PreprintServerRegistry
            Registry populated with the provided clients.
        """
        registry = cls()
        registry.register_all(clients)
        return registry


def default_registry() -> PreprintServerRegistry:
    """Create a registry seeded with built-in preprint server clients.

    Returns
    -------
    PreprintServerRegistry
        Registry populated with the project's built-in server clients.
    """
    from peer_elt.extract.biorxiv import BiorxivApiClient

    return PreprintServerRegistry.from_clients(
        [
            BiorxivApiClient(server="biorxiv"),
            BiorxivApiClient(server="medrxiv"),
        ]
    )


class RegistryExtractor(Extractor):
    """Extractor that delegates to a :class:`PreprintServerRegistry`.

    Parameters
    ----------
    registry : PreprintServerRegistry | None, default=None
        Registry used to look up clients by ``source.server``. If None,
        :func:`default_registry` is used.

    Notes
    -----
    If the fetched dataframe does not contain a ``server`` column, this extractor
    adds it using ``source.server`` (copying the frame first to avoid mutating
    shared data).
    """

    def __init__(self, registry: PreprintServerRegistry | None = None) -> None:
        self._registry = registry or default_registry()

    def fetch(self, source: SourceConfig, retry_config: RetryConfig) -> pd.DataFrame:
        """Fetch records for a configured source by dispatching to a registered client.

        Parameters
        ----------
        source : peer_elt.config.SourceConfig
            Source configuration (server slug and date window).
        retry_config : peer_elt.config.RetryConfig
            Retry/backoff configuration forwarded to the underlying client.

        Returns
        -------
        pandas.DataFrame
            Raw metadata rows for the requested source window.
        """
        client = self._registry.get(source.server)
        frame = client.fetch(source.date_from, source.date_to, retry_config)
        if frame.empty:
            return frame
        if "server" not in frame.columns:
            frame = frame.copy()
            frame["server"] = source.server
        return frame
