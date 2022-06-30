"""RDMAStore Implementation."""
from __future__ import annotations

import logging
import time
import struct  # need to handle this in rdma_transfer.c instead
from typing import Any


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
        store: dict,
        provider: int = 42,
        max_transfer: int = (514*1024**2) // 4,
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
        self.provider = provider
        self.max_transfer = max_transfer
        self.store = store
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
        kwargs.update({"addr": self.addr, "store": self.store, "max_transfer": self.max_transfer, "provider": self.provider })
        return super()._kwargs(kwargs)

    def evict(self, key: str) -> None:
        """Evict object associated with key from Redis.

        Args:
            key (str): key corresponding to object in store to evict.
        """

        # TODO: implement in rdma transfer
        self._cache.evict(key)
        logger.debug(
            f"EVICT key='{key}' FROM {self.__class__.__name__}" f"(name='{self.name}')",
        )

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis.

        Args:
            key (str): key to check.

        Returns:
            `bool`
        """
        # TODO: implement in rdma transfer
        return False

    def get_bytes(self, key: str) -> bytes | None:
        """Get serialized object from Remote location.

        Args:
            key (str): key corresponding to object.

        Returns:
            serialized object or `None` if it does not exist.
        """
        with Engine('tcp', mode=pymargo.client) as engine:
            rpc_id = engine.register("get")
            buff = np.array([" " * self.max_transfer], dtype=bytes)  # equivalent to malloc
            blk = engine.create_bulk(buff, bulk.read_write)
            s = blk.to_base64()
            call_rpc_on(engine, rpc_id, self.addr, self.provider, s, key, self.max_transfer)
            print(buff[0].strip())
        if key not in self.store:
            return None
        return self.store[key] #buff[0].strip()

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
        with Engine('tcp', mode=pymargo.client) as engine:
            rpc_id = engine.register("get")
            buff = np.array([" " * self.max_transfer], dtype=str)  # equivalent to malloc
            blk = engine.create_bulk(buff, bulk.read_write)
            s = blk.to_base64()
            call_rpc_on(engine, rpc_id, self.addr, self.provider, s, key + "_timestamp", self.max_transfer)
            value = buff[0:10].strip()

            if value is None:
                raise KeyError(f"Key='{key}' does not exist on the remote server")

        print("val", value)
        return self.store[key + "_timestamp"] #time.time() #value.decode("utf-8")  # struct.unpack("<d", value)

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
        print("test")
        return super().proxy(obj, key=key, factory=factory, **kwargs)

    def set_bytes(self, key: str, data: bytes) -> None:
        """Set serialized object in Remote server with key.

        Args:
            key (str): key corresponding to object.
            data (bytes): serialized object.
        """
        if not isinstance(data, bytes):
            raise TypeError(f"data must be of type bytes. Found {type(data)}")
        # We store the creation time for the key as a separate file.
        with Engine('tcp', mode=pymargo.client) as engine:
            rpc_id = engine.register("set")
            buff = np.array([str(time.time()).encode()], dtype=str)  # equivalent to malloc
            blk = engine.create_bulk(buff, bulk.read_write)
            print(buff[0])
            s = blk.to_base64()
            call_rpc_on(engine, rpc_id, self.addr, self.provider, s, key + "_timestamp", len(buff))
            buff = np.array([data], dtype=bytes)  # equivalent to malloc
            blk = engine.create_bulk(buff, bulk.read_write)
            s = blk.to_base64()
            call_rpc_on(engine, rpc_id, self.addr, self.provider, s, key, len(data))
        self.store[key + "_timestamp"] = time.time()
        self.store[key] = data


def call_rpc_on(engine, rpc_id, addr_str, provider_id, array_str, key, size):
    addr = engine.lookup(addr_str)
    handle = engine.create_handle(addr, rpc_id)
    data = {"key": key, "size": size, "buffer": array_str}  # , "buffer": array_str }
    serialized = json.dumps(data)
    return handle.forward(provider_id, serialized)
