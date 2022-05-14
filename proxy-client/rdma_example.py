#!/usr/bin/env python
import sys
import rdma as proxy_rdma

addr = sys.argv[1]
store = proxy_rdma.RDMAStore(name="rdma", addr=addr)
x = "hello world!"
p = store.proxy(x)

print(p)
