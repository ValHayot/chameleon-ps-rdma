#!/usr/bin/env python
import sys
import proxystore as ps
import random
import examples

REDIS_HOST = sys.argv[1]
REDIS_PORT = sys.argv[2]
store = ps.store.init_store(
    'redis', name='redis', hostname=REDIS_HOST, port=REDIS_PORT
)

examples.run_ex(store)
