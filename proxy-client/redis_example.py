#!/usr/bin/env python
import sys
import proxystore as ps

REDIS_HOST = sys.argv[1]
REDIS_PORT = sys.argv[2]
store = ps.store.init_store(
    'redis', name='redis', hostname=REDIS_HOST, port=REDIS_PORT
)

x = "hello world!"
p = store.proxy(x)

y = "foo bar"
q = store.proxy(y)

print(q)
print(p)
