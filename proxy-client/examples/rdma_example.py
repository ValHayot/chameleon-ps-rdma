#!/usr/bin/env python
import sys
import rdma as proxy_rdma
import random
import string
import examples

def randStr(chars = string.ascii_uppercase + string.digits, N=10):
	return ''.join(random.choice(chars) for _ in range(N))

addr = sys.argv[1]
store = proxy_rdma.RDMAStore(name="rdma", addr=addr)

examples.run_ex(store)

#for i in range(0, 500, 10):
#    z = store.proxy(randStr(N=10*(i+1)))
#    print(z)
