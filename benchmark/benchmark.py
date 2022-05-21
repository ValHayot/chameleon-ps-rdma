#!/usr/bin/env python
import sys
import gc
import random
from functools import wraps

# import rdma as proxy_rdma
import click

import proxystore as ps

from time import perf_counter_ns


def bench(size, logfile, cmd):
    def bench_decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            start = perf_counter_ns()
            func()
            end = perf_counter_ns()
            duration = (end - start) * 10**-9
            print(f"{cmd=}, {func.__name__=}, {size=}, {start=}, {end=}, {duration=}")
            # Open the logfile and append
            with open(logfile, 'a+') as f:
                f.write(f"{cmd=},{func.__name__},{size},{start},{end},{duration=}\n")
            return func(*args, **kwargs)
        return wrapped_function
    return bench_decorator


def run(store, logfile, cmd):
    min_exp = 10  # approx 1 KB
    max_exp = 31  # approx 1 GB

    proxies = {}

    print("Running write benchmarks...")
    for i in ( 2 ** i for i in range(min_exp, max_exp, 5) ):
        data = "a"*i

        b = sys.getsizeof(data)
        @bench(size=b, logfile=logfile, cmd=cmd)
        def store_data():
             y = store.proxy(data)
             return y

        y = store_data()
        proxies[y] = b

    # attempting to remove from caches
    for k, v in proxies.items():
        store._cache.evict(k)

    gc.collect()

    print("Running read benchmarks...")
    for k, v in proxies.items():

        @bench(size=v, logfile=logfile, cmd=cmd)
        def load_proxy():
             z = "".join([c for c in k])
             return z
     
        z = load_proxy()


@click.group()
@click.option("--logfile", type=str, default="out.log")
@click.pass_context
def cli(ctx, logfile):
    ctx.ensure_object(dict)
    ctx.obj["log"] = logfile


@cli.command()
@click.pass_context
@click.argument("addr")
def mochi(ctx, addr):
    sys.path.insert(0,'../proxy-client')
    import rdma as proxy_rdma
    store = proxy_rdma.RDMAStore(name="rdma", addr=addr)
    run(store, logfile=ctx.obj["log"], cmd="mochi")


@cli.command()
@click.pass_context
@click.argument("host")
@click.argument("port")
def redis(ctx, host, port):

    store = ps.store.init_store("redis", name="redis", hostname=host, port=port)

    run(store, ctx.obj["log"], cmd="redis")


if __name__ == "__main__":
    cli(obj={})
