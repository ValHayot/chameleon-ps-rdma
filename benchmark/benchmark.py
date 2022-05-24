#!/usr/bin/env python
import sys
import gc
import random
from functools import wraps
from typing import Optional

# import rdma as proxy_rdma
import click

import proxystore as ps

from time import perf_counter_ns


class Benchmark:
    def __init__(
        self,
        connect,
        *,
        cmd: str,
        logfile: Optional[None],
        reps: int,
        overwrite: bool = True,
        **kwargs,
    ):
        self.cmd = cmd
        self.logfile = logfile
        self.reps = reps
        self.proxies = {}

        if logfile is not None and overwrite:
            # overwrite logfile and write header
            with open(logfile, "w+") as f:
                f.write("store,function,size,start,end,duration\n")

        self.store = self.bench(0)(connect)(cmd, **kwargs)

    def run(self):
        OKGREEN = "\033[92m"
        OKENDC = "\033[0m"
        BOLD = "\033[1m"

        def print_status(func, text, *args):
            if self.logfile is None:
                end = "\n"
            else:
                end = ""

            print(text, end=end, flush=True)

            for i in range(self.reps):
                if self.logfile is not None:
                    print(".", end=end, flush=True)
                else:
                    print("\n\n")
                func(*args)

            print(f"{OKGREEN}done{OKENDC}")

        print_status(self.write, f"Running {BOLD}write{OKENDC} benchmarks")

        if self.cmd != "local":
            print_status(self.read, f"Running {BOLD}cached read{OKENDC} benchmarks", True)

            # attempting to remove from caches
            self.cache_evict()

        print_status(self.read, f"Running {BOLD}read{OKENDC} benchmarks")

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
        suffix = ""
        if cached:
            suffix = "_cached"
        for k, v in self.proxies.items():

            @self.bench(size=v, task_suffix=suffix)
            def load_proxy():
                z = len(k)
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
                func_name = f"{func.__name__}{task_suffix}"

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
@click.option("--logfile", type=str, default=None)
@click.option("--reps", type=int, default=1)
@click.option("--overwrite", is_flag=True)
@click.pass_context
def cli(ctx, logfile, reps, overwrite):
    ctx.ensure_object(dict)
    ctx.obj["logfile"] = logfile
    ctx.obj["reps"] = reps
    ctx.obj["overwrite"] = overwrite


@cli.command()
@click.pass_context
@click.argument("addr")
def mochi(ctx, addr):
    sys.path.insert(0, "../proxy-client")
    import rdma as proxy_rdma

    b = Benchmark(proxy_rdma.RDMAStore, name="rdma", addr=addr, logfile=ctx.obj["log"])
    b.run()


@cli.command()
@click.pass_context
@click.argument("host")
@click.argument("port")
def redis(ctx, host, port):

    b = Benchmark(
        ps.store.init_store,
        cmd="redis",
        name="redis",
        hostname=host,
        port=port,
        **ctx.obj
    )

    b.run()

@cli.command()
@click.pass_context
def local(ctx):

    b = Benchmark(
        ps.store.init_store,
        cmd="local",
        name="local",
        **ctx.obj
    )
    b.run()


@cli.command()
@click.pass_context
@click.argument("store_dir")
def file(ctx, store_dir):

    b = Benchmark(
        ps.store.init_store,
        cmd="file",
        name="file",
        store_dir=store_dir,
        **ctx.obj
    )
    b.run()


@cli.command()
@click.pass_context
@click.argument("endpoint_json")
def globus(ctx, endpoint_json):
    endpoints = ps.store.globus.GlobusEndpoints.from_json(endpoint_json)
    print(endpoints)

    b = Benchmark(
        ps.store.init_store,
        cmd="globus",
        name="globus",
        endpoints=endpoints,
        **ctx.obj
    )
    b.run()


if __name__ == "__main__":
    cli(obj={})
