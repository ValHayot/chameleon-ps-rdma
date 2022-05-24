#!/usr/bin/env python
import sys
import gc
import random
from functools import wraps

# import rdma as proxy_rdma
import click

import proxystore as ps

from time import perf_counter_ns


class Benchmark:
    def __init__(self, connect, *, cmd, logfile, **kwargs):
        self.cmd = cmd
        self.logfile = logfile
        self.proxies = {}

        if logfile is not None:
            # overwrite logfile and write header
            with open(logfile, "w+") as f:
                f.write("store,function,size,start,end,duration\n")

        self.store = self.bench(0)(connect)(cmd, **kwargs)

    def run(self):
        OKGREEN = "\033[92m"
        OKENDC = "\033[0m"

        def print_status(func, text):
            print(text, end="", flush=True)
            func()
            print(f"{OKGREEN}done{OKENDC}")

        print_status(self.write, "Running write benchmarks...")
        print_status(self.read, "Running cached read benchmarks...")

        # attempting to remove from caches
        self.cache_evict()

        print_status(self.read, "Running read benchmarks...")

    def write(self):
        min_exp = 10  # approx 1 KB
        max_exp = 29  # 512MB is the redis string limit, but python strings are never exactly a certain number of bytes

        for i in (2**i for i in range(min_exp, max_exp)):
            data = "a" * i

            b = sys.getsizeof(data)

            @self.bench(size=b)
            def store_data():
                y = self.store.proxy(data)
                return y

            y = store_data()
            self.proxies[y] = b

    def read(self, cached=False):
        task = None
        if cached:
            task = "cached"
        for k, v in self.proxies.items():

            @self.bench(size=v, task_suffix=task)
            def load_proxy():
                z = "".join([c for c in k])
                return z

            z = load_proxy()

    def cache_evict(self):
        for k, v in self.proxies.items():
            self.store._cache.evict(k)

        gc.collect()

    def bench(self, size, task_suffix=""):
        cmd = self.cmd

        def bench_decorator(func):
            @wraps(func)
            def wrapped_function(*args, **kwargs):
                func_name = f"{func.__name__}_{task_suffix}"

                start = perf_counter_ns()
                func(*args, **kwargs)
                end = perf_counter_ns()
                duration = (end - start) * 10**-9

                # Open the logfile and append
                if self.logfile is not None:
                    with open(self.logfile, "a+") as f:
                        f.write(f"{cmd},{func_name},{size},{start},{end},{duration}\n")
                else:
                    print(
                        f"{self.cmd=}, {func_name=}, {size=}, {start=}, {end=}, {duration=}"
                    )
                return func(*args, **kwargs)

            return wrapped_function

        return bench_decorator


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
    sys.path.insert(0, "../proxy-client")
    import rdma as proxy_rdma

    store = proxy_rdma.RDMAStore(name="rdma", addr=addr)
    run(store, logfile=ctx.obj["log"], cmd="mochi")


@cli.command()
@click.pass_context
@click.argument("host")
@click.argument("port")
def redis(ctx, host, port):

    store = Benchmark(
        ps.store.init_store,
        cmd="redis",
        name="redis",
        hostname=host,
        port=port,
        logfile=ctx.obj["log"],
    )
    store.run()


if __name__ == "__main__":
    cli(obj={})
