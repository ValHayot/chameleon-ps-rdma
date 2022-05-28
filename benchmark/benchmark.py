#!/usr/bin/env python
import sys
import gc
import random
from os import path as op, system
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
        name: str,
        logfile: Optional[None],
        overwrite: bool = True,
        **kwargs,
    ):
        self.cmd = name
        self.logfile = logfile
        self.proxies = {}

        if logfile is not None and (overwrite or not op.exists(logfile)):
            # overwrite logfile and write header
            with open(logfile, "w+") as f:
                f.write("store,function,size,start,end,duration\n")
        
        if cmd == "rdma":
            self.store = self.bench(0)(connect)(name, **kwargs)

        else:
            self.store = self.bench(0)(connect)(cmd, name, **kwargs)

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

            func(*args)

            print(f"{OKGREEN}done{OKENDC}")

        print_status(self.write, f"Running {BOLD}write{OKENDC} benchmarks...")

        if self.cmd != "local":
            print_status(self.read, f"Running {BOLD}cached read{OKENDC} benchmarks...", True)

            # attempting to remove from caches
            self.cache_evict()

        print_status(self.read, f"Running {BOLD}read{OKENDC} benchmarks...")

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

        try:
            #drop page cache
            system('sudo sh -c "sync; echo 3 > /proc/sys/vm/drop_caches"')
        except Exception as e:
            print(f"ERROR: unable to drop caches due to -- {str(e)}")

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


def run_reps(func, **kwargs):
    reps = kwargs.pop("reps")
    for i in range(reps):
        print(f"***Repetition {i}***")
        b = Benchmark(func, **kwargs)
        b.run()


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

    run_reps(
        proxy_rdma.RDMAStore,
        cmd="rdma",
        name="rdma",
        addr=addr,
        **ctx.obj
    )


@cli.command()
@click.pass_context
@click.argument("host")
@click.argument("port")
def redis(ctx, host, port):

    run_reps(
        ps.store.init_store,
        cmd="redis",
        name="redis",
        hostname=host,
        port=port,
        **ctx.obj
    )


@cli.command()
@click.pass_context
@click.argument("host")
@click.argument("port")
def keydb(ctx, host, port):

    run_reps(
        ps.store.init_store,
        cmd="redis",
        name="keydb",
        hostname=host,
        port=port,
        **ctx.obj
    )


@cli.command()
@click.pass_context
def local(ctx):

    run_reps(
        ps.store.init_store,
        cmd="local",
        name="local",
        **ctx.obj
    )


@cli.command()
@click.pass_context
@click.argument("store_dir")
def file(ctx, store_dir):

    run_reps(
        ps.store.init_store,
        cmd="file",
        name="file",
        store_dir=store_dir,
        **ctx.obj
    )


@cli.command()
@click.pass_context
@click.argument("endpoint_json")
def globus(ctx, endpoint_json):
    endpoints = ps.store.globus.GlobusEndpoints.from_json(endpoint_json)

    # hardcoding timeout for now
    run_reps(
        ps.store.init_store,
        cmd="globus",
        name="globus",
        endpoints=endpoints,
        timeout=3600,
        **ctx.obj
    )


if __name__ == "__main__":
    cli(obj={})
