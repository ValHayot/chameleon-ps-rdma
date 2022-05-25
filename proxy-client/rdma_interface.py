#!/usr/bin/env python
import asyncio
import rdma_transfer as rt


class RDMA:

    def __init__(self, addr):
        self.addr = addr
        self.connect()

    def set(self, key, value):
        return rt.set(key, value)

    def get(self, key, size=None):
        if size is None:
            size = 512*1024**2 # reserve a 512MB buffer
        return rt.get(key, size)

    def connect(self):
        rt.connect(self.addr)

    def disconnect(self):
        rt.disconnect()



