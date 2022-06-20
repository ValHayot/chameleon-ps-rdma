#!/usr/bin/env python
import numpy as np
import pymargo
from pymargo.core import Engine
import pymargo.bulk as bulk
import json


class RDMA:

    def __init__(self, addr, provider_id, max_size = 50*1024**2):
        self.engine = Engine('tcp', mode=pymargo.client) 
        #self.addr = self.engine.lookup(addr)
        self.addr = addr
        self.provider_id = provider_id
        #self.max_size = max_size
        #self.rpcs = { "get": self.engine.register("get"), "set": self.engine.register("set") }

    def set(self, key, value):
        #with Engine('tcp', mode=pymargo.client) as engine:
        buff = np.chararray(shape=len(value), buffer=value)  # equivalent to malloc
        blk = self.engine.create_bulk(buff, bulk.read_write)
        s = blk.to_base64()
        self.call_rpc_on(self.engine.register("set"), s, key, buff.size*buff.itemsize)
        return None

    def get(self, key, size=None):
        if size is None:
            size = self.get_size(key)

        buff = np.chararray(size)  # equivalent to malloc

        #with Engine('tcp', mode=pymargo.client) as engine:
        blk = self.engine.create_bulk(buff, bulk.read_write)
        s = blk.to_base64()
        self.call_rpc_on(self.engine.register("get"), s, key, size)
        return buff.view('S' + str(buff.size))[0]

    def get_size(self, key):
        buff = np.empty(1, dtype=np.uint64)
        blk = self.engine.create_bulk(buff, bulk.read_write)
        s = blk.to_base64()
        self.call_rpc_on(self.engine.register("get_size"), s, key, buff.itemsize)
        return int(buff)
        

    def exists(self, key, size=None):
        #with Engine('tcp', mode=pymargo.client) as engine:
        buff = np.array([False], dtype=bool)  # equivalent to malloc
        blk = engine.create_bulk(buff, bulk.read_write)
        s = blk.to_base64()
        self.call_rpc_on(self.engine.register("exists"), s, key, buff.itemsize)
        return buff[0]

    def call_rpc_on(self, rpc, array_str, key, size):
         handle = self.engine.create_handle(self.engine.lookup(self.addr), rpc)
         data = {"key": key, "size": size, "buffer": array_str}  # , "buffer": array_str }
         serialized = json.dumps(data)
         return handle.forward(self.provider_id, serialized)
