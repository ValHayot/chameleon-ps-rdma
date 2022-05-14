"""RDMAStore Implementation."""
from __future__ import annotations

import logging
import time
import struct # need to handle this in rdma_transfer.c instead
from typing import Any

import rdma_transfer as rt

import proxystore as ps
from proxystore.store.remote import RemoteFactory
from proxystore.store.remote import RemoteStore

logger = logging.getLogger(__name__)


class RDMAFactory(RemoteFactory):
    """Factory for Instances of RDMAStore."""

    def __init__(
        self,
        key: str,
        store_name: str,
        store_kwargs: dict[str, Any] | None = None,
        *,
        evict: bool = False,
        serialize: bool = True,
        strict: bool = False,
    ) -> None:
        """Init RDMAFactory.

        Args:
            key (str): key corresponding to object in store.
            store_name (str): name of store.
            store_kwargs (dict): optional keyword arguments used to
                reinitialize store.
            evict (bool): If True, evict the object from the store once
                :func:`resolve()` is called (default: False).
            serialize (bool): if True, object in store is serialized and
                should be deserialized upon retrieval (default: True).
            strict (bool): guarantee object produce when this object is called
                is the most recent version of the object associated with the
                key in the store (default: False).
        """
        super().__init__(
            key,
            RDMAStore,
            store_name,
            store_kwargs,
            evict=evict,
            serialize=serialize,
            strict=strict,
        )


class RDMAStore(RemoteStore):
    """Redis backend class."""

    def __init__(
        self,
        name: str,
        *,
        addr: str,
        **kwargs: Any,
    ) -> None:
        """Init RDMAStore.

        Args:
            name (str): name of the store instance.
            addr (str): RDMA server address in the form <protocol>://<ip>:<port>.
            kwargs (dict): additional keyword arguments to pass to
                :class:`RemoteStore <proxystore.store.remote.RemoteStore>`.
        """
        self.addr = addr
        rt.connect(self.addr)
        super().__init__(name, **kwargs)

    def _kwargs(
        self,
        kwargs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Helper for handling inheritance with kwargs property.

        Args:
            kwargs (optional, dict): dict to use as return object. If None,
                a new dict will be created.
        """
        if kwargs is None:
            kwargs = {}
        kwargs.update({'addr': self.addr})
        return super()._kwargs(kwargs)

    def evict(self, key: str) -> None:
        """Evict object associated with key from Redis.

        Args:
            key (str): key corresponding to object in store to evict.
        """

        #TODO: implement in rdma transfer
        self._cache.evict(key)
        logger.debug(
            f"EVICT key='{key}' FROM {self.__class__.__name__}"
            f"(name='{self.name}')",
        )

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis.

        Args:
            key (str): key to check.

        Returns:
            `bool`
        """
        #TODO: implement in rdma transfer
        return False

    def get_bytes(self, key: str) -> bytes | None:
        """Get serialized object from Remote location.

        Args:
            key (str): key corresponding to object.

        Returns:
            serialized object or `None` if it does not exist.
        """
        return rt.get(key)

    def get_timestamp(self, key: str) -> float:
        """Get timestamp of most recent object version in the store.

        Args:
            key (str): key corresponding to object.

        Returns:
            timestamp (float) of when key was added to remote server (seconds since
            epoch).

        Raises:
            KeyError:
                if `key` does not exist in store.
        """
        value = rt.get(key + '_timestamp')
        if value is None:
            raise KeyError(f"Key='{key}' does not exist on the remote server")
        return struct.unpack("<d", value)

    def proxy(  # type: ignore[override]
        self,
        obj: Any | None = None,
        *,
        key: str | None = None,
        factory: type[RemoteFactory] = RDMAFactory,
        **kwargs: Any,
    ) -> ps.proxy.Proxy:
        """Create a proxy that will resolve to an object in the store.

        Args:
            obj (object): object to place in store and return proxy for.
                If an object is not provided, a key must be provided that
                corresponds to an object already in the store (default: None).
            key (str): optional key to associate with `obj` in the store.
                If not provided, a key will be generated (default: None).
            factory (Factory): factory class that will be instantiated
                and passed to the proxy. The factory class should be able
                to correctly resolve the object from this store
                (default: :class:`RDMAFactory <.RDMAFactory>`).
            kwargs (dict): additional arguments to pass to the Factory.

        Returns:
            :any:`Proxy <proxystore.proxy.Proxy>`

        Raises:
            ValueError:
                if `key` and `obj` are both `None`.
        """
        return super().proxy(obj, key=key, factory=factory, **kwargs)

    def set_bytes(self, key: str, data: bytes) -> None:
        """Set serialized object in Remote server with key.

        Args:
            key (str): key corresponding to object.
            data (bytes): serialized object.
        """
        if not isinstance(data, bytes):
            raise TypeError(f'data must be of type bytes. Found {type(data)}')
        # We store the creation time for the key as a separate file.
        rt.set((key + '_timestamp', struct.pack('<d', time.time())))
        rt.set((key, data))
