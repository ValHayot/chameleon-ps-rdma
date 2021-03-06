"""RedisStore Implementation."""
from __future__ import annotations

import logging
import time

import redis

from proxystore.store.rdma_interface import RDMA

from proxystore.store.base import Store

logger = logging.getLogger(__name__)


is_init = False
class MargoStore(Store):
    """Redis backend class."""

    def __init__(
        self,
        name: str,
        *,
        addr_str: str,
        provider_id: int,
        cache_size: int = 16,
        stats: bool = False,
        _mochi : RDMA | None = None, #temp hack to not start up client multiple times
    ) -> None:
        """Init RedisStore.

        Args:
            name (str): name of the store instance.
            hostname (str): Redis server hostname.
            port (int): Redis server port.
            cache_size (int): size of LRU cache (in # of objects). If 0,
                the cache is disabled. The cache is local to the Python
                process (default: 16).
            stats (bool): collect stats on store operations (default: False).
        """
        self.addr = addr_str
        self.provider_id = provider_id
        if _mochi is None:
            self._mochi = RDMA(addr=addr_str, provider_id=provider_id)
        else:
            self._mochi = _mochi
        
        super().__init__(
            name,
            cache_size=cache_size,
            stats=stats,
            kwargs={'addr_str': self.addr, 'provider_id': self.provider_id, '_mochi': self._mochi },
        )

    def evict(self, key: str) -> None:
        self._cache.evict(key)
        logger.debug(
            f"EVICT key='{key}' FROM {self.__class__.__name__}"
            f"(name='{self.name}')",
        )

    def exists(self, key: str) -> bool:
        return bool(self._mochi.exists(key))

    def get_bytes(self, key: str) -> bytes | None:
        return self._mochi.get(key)

    def get_timestamp(self, key: str) -> float:
        value = self._mochi.get(key + '_timestamp')
        if value is None:
            raise KeyError(f"Key='{key}' does not exist in Redis store")
        return float(value.decode())

    def set_bytes(self, key: str, data: bytes) -> None:
        # We store the creation time for the key as a separate redis key-value.
        self._mochi.set(key + '_timestamp', str(time.time()).encode())
        self._mochi.set(key, data)
