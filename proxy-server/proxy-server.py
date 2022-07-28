#!/uiisr/bin/env python

import os
import json
import daemon
import signal
import numpy as np

from functools import partial
from time import sleep

import pymargo.client
import pymargo.bulk as bulk
from pymargo.core import Engine, Provider
from pymargo.bulk import Bulk


class RDMAClient():

    peer_dir = os.path.join(os.path.expanduser('~'), ".proxystore", "peers")

    def __init__(self, host, port, max_size = 50*1024**2, peer_dir=None):

        if peer_dir is not None:
            self.peer_dir = peer_dir

        else:
            peer_dir = os.path.join(os.path.expanduser('~'), ".proxystore", "peers")

        # Check if peer directory exists
        if not os.path.exists(peer_dir):
            os.makedirs(peer_dir)

        # Get all existing peer services
        self.peers = {}
        self._update_peers()

        # Start peer service. Using a daemon as wait_for_finalize hangs
        with daemon.DaemonContext():
            addr = f"tcp://{host}:{port}" # tcp for now, maybe UCX later?
            engine = Engine(addr)
            provider_id = os.getpid()

            peer_file = os.path.join(self.peer_dir, f"peer_{provider_id}.json")

            with open(peer_file, "w+") as f:
                json.dump({ "addr": addr, "provider_id": provider_id }, f)

            print(
                "Server running at address "
                + str(engine.addr())
                + " with provider_id "
                + str(provider_id)
            )

            engine.on_finalize(WhenFinalize)
            engine.enable_remote_shutdown()

            signal.signal(signal.SIGINT, partial(handler, engine))

            RDMAProvider(engine, provider_id)

            engine.wait_for_finalize()


    def __enter__(self):
        return self

    def __exit__(self):
        self.engine.close()

    def _update_peers(self):
        """ Update the peer dictionary to include any new peers that may have just joined.
        The communication is done via the shared filesystem for the moment.

        Returns:
            A list of tuples containing the details of the new peers
        """
        new_peers = []

        for fn in os.listdir(self.peer_dir):
            with open(self.join(self.peer_dir, fn), "r+") as f:
                peer_data = json.load(f)

            if peer_data["addr"] not in self.peers:
                self.peers[peer_data["addr"]] = { peer_data["provider_id"] }
                new_peers.append((peer_data["addr"]))

        return new_peers





    def set(self, key, value):
        buff = np.chararray(shape=len(value), buffer=value)  # equivalent to malloc
        blk = self.engine.create_bulk(buff, bulk.read_write)
        s = blk.to_base64()
        self.call_rpc_on(self.rpcs["set"], s, key, buff.size*buff.itemsize)
        return None

    def get(self, key, size=None):
        if size is None:
            size = self.get_size(key)

        buff = np.chararray(size)  # equivalent to malloc

        #with Engine('tcp', mode=pymargo.client) as engine:
        blk = self.engine.create_bulk(buff, bulk.read_write)
        s = blk.to_base64()
        self.call_rpc_on(self.rpcs["get"], s, key, size)
        return buff.view('S' + str(buff.size))[0]

    def get_size(self, key):
        buff = np.empty(1, dtype=np.uint64)
        blk = self.engine.create_bulk(buff, bulk.read_write)
        s = blk.to_base64()
        self.call_rpc_on(self.engine.register("get_size"), s, key, buff.itemsize)
        return int(buff)

    def exists(self, key, size=None):
        buff = np.array([False], dtype=bool)  # equivalent to malloc
        blk = self.engine.create_bulk(buff, bulk.read_write)
        s = blk.to_base64()
        self.call_rpc_on(self.engine.register("exists"), s, key, buff.itemsize)
        return buff[0]

    def call_rpc_on(self, rpc, array_str, key, size):
         handle = self.engine.create_handle(self.engine.lookup(self.addr), rpc)
         data = {"key": key, "size": size, "buffer": array_str}  # , "buffer": array_str }
         serialized = json.dumps(data)
         print("hello 2")
         return handle.forward(self.provider_id, serialized)

class RDMAProvider(Provider):
    def __init__(self, engine, provider_id):
        super().__init__(engine, provider_id)
        self.register("get", "get")
        self.register("get_size", "get_size")
        self.register("set", "set")
        self.register("exists", "exists")
        self.data = {}

    def set(self, handle, bulk_str):
        data = json.loads(bulk_str)
        print("Received set RPC")

        engine = self.get_engine()
        #print("data size", data["size"])
        localArray = np.chararray(data["size"])
        try:
            localBulk = engine.create_bulk(localArray, bulk.write_only)
            remoteBulk = Bulk.from_base64(engine, data["buffer"])
            #print("Remote bulk deserialized")
            size = localArray.itemsize * localArray.size
            engine.transfer(
                bulk.pull, handle.get_addr(), remoteBulk, 0, localBulk, 0, size
            )
        except Exception as error:
            print("An exception was caught:")
            print(error)
        #print("Transfer done")
        self.data[data["key"]] = localArray
        handle.respond("OK")

    def get(self, handle, bulk_str):
        #print("Received get RPC")
        data = json.loads(bulk_str)

        engine = self.get_engine()
        localArray = np.chararray(shape=len(self.data[data["key"]]), buffer=self.data[data["key"]])
        try:
            localBulk = engine.create_bulk(localArray, bulk.read_only)
            remoteBulk = Bulk.from_base64(engine, data["buffer"])
            #print("Remote bulk deserialized", data["key"], localArray.itemsize * localArray.size)
            size = localArray.itemsize * localArray.size
            engine.transfer(
                bulk.push, handle.get_addr(), remoteBulk, 0, localBulk, 0, size
            )
        except Exception as error:
            print("An exception was caught:")
            print(error)
        #print("Transfer done")
        handle.respond("OK")


    def get_size(self, handle, bulk_str):
        data = json.loads(bulk_str)

        engine = self.get_engine()
        localArray = np.array([self.data[data["key"]].size], dtype=np.uint64)
        try:
            localBulk = engine.create_bulk(localArray, bulk.read_only)
            remoteBulk = Bulk.from_base64(engine, data["buffer"])
            #print("Remote bulk deserialized", data["key"], localArray.itemsize * localArray.size)
            size = localArray.itemsize * localArray.size
            engine.transfer(
                bulk.push, handle.get_addr(), remoteBulk, 0, localBulk, 0, size
            )
        except Exception as error:
            print("An exception was caught:")
            print(error)
        #print("Transfer done")
        handle.respond("OK")

    def exists(self, handle, bulk_str):
        #print("Received exists RPC")
        data = json.loads(bulk_str)

        engine = self.get_engine()
        localArray = np.array([data["key"] in self.data], dtype=bool)
        try:
            localBulk = engine.create_bulk(localArray, bulk.read_only)
            remoteBulk = Bulk.from_base64(engine, data["buffer"])
            #print("Remote bulk deserialized", data["key"], localArray.itemsize)
            size = localArray.itemsize
            engine.transfer(
                bulk.push, handle.get_addr(), remoteBulk, 0, localBulk, 0, size
            )
        except Exception as error:
            print("An exception was caught:")
            print(error)
        #print("Transfer done")
        handle.respond("OK")

def handler(engine, *args):
    engine.finalize()

def WhenFinalize():
    print("Finalize was called")