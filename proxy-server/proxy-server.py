#!/usr/bin/env python

import json
import daemon
import numpy as np
import pymargo.bulk as bulk
from pymargo.core import Engine, Provider
from pymargo.bulk import Bulk

import click


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
        #print("Received set RPC")

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


def WhenFinalize():
    print("Finalize was called")


@click.command()
@click.argument("host")
@click.argument("port")
def main(host, port):
    #with daemon.DaemonContext():
        print(host, port)
        addr = f"tcp://{host}:{port}"
        engine = Engine(addr)
        provider_id = 42
        print(
            "Server running at address "
            + str(engine.addr())
            + " with provider_id "
            + str(provider_id)
        )

        engine.on_finalize(WhenFinalize)
        provider = RDMAProvider(engine, provider_id)
        engine.wait_for_finalize()


if __name__ == "__main__":
    main()
