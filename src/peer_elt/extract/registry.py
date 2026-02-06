from __future__ import annotations

"""Framework for registering and accessing preprint server clients."""

from abc import ABC, abstractmethod
from typing import Dict, Iterable, List

import pandas as pd

from peer_elt.config import RetryConfig, SourceConfig
from peer_elt.interfaces import Extractor


class PreprintServerClient(ABC):
    """Client interface for pulling metadata from a preprint server."""

    server: str

    @abstractmethod
    def fetch(
            self,
            date_from: str,
            date_to: str,
            retry_config: RetryConfig,
    ) -> pd.DataFrame:
        """Fetch raw metadata from a server for the date window."""
        raise NotImplementedError


class PreprintServerRegistry:
    """Registry for available preprint server clients."""

    def __init__(self) -> None:
        self._clients: Dict[str, PreprintServerClient] = {}

    def register(self, client: PreprintServerClient) -> None:
        if client.server in self._clients:
            raise ValueError(f"Client already registered for server: {client.server}")
        self._clients[client.server] = client

    def has_server(self, server: str) -> bool:
        return server in self._clients

    def get(self, server: str) -> PreprintServerClient:
        try:
            return self._clients[server]
        except KeyError as exc:
            raise ValueError(f"Unsupported source server: {server}") from exc

    def supported_servers(self) -> List[str]:
        return sorted(self._clients.keys())

    def register_all(self, clients: Iterable[PreprintServerClient]) -> None:
        for client in clients:
            self.register(client)

    @classmethod
    def from_clients(cls, clients: Iterable[PreprintServerClient]) -> "PreprintServerRegistry":
        registry = cls()
        registry.register_all(clients)
        return registry


def default_registry() -> PreprintServerRegistry:
    """Create a registry seeded with built-in preprint server clients."""
    from peer_elt.extract.biorxiv import BiorxivApiClient

    return PreprintServerRegistry.from_clients(
        [
            BiorxivApiClient(server="biorxiv"),
            BiorxivApiClient(server="medrxiv"),
        ]
    )


class RegistryExtractor(Extractor):
    """Extractor that pulls data from registered preprint server clients."""

    def __init__(self, registry: PreprintServerRegistry | None = None) -> None:
        self._registry = registry or default_registry()

    def fetch(self, source: SourceConfig, retry_config: RetryConfig) -> pd.DataFrame:
        client = self._registry.get(source.server)
        frame = client.fetch(source.date_from, source.date_to, retry_config)
        if frame.empty:
            return frame
        if "server" not in frame.columns:
            frame = frame.copy()
            frame["server"] = source.server
        return frame
