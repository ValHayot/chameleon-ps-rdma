#!/usr/bin/env python


def run_ex(store):
    x = "hello world!"
    p = store.proxy(x)

    y = "foo bar"
    q = store.proxy(y)

    with open("output5.dat", "r") as f:
        data = f.read()
        print(f"data length = {len(data)}")
        t = store.proxy(data)

    with open("output150.dat", "r") as f:
        data = f.read()
        print(f"data length = {len(data)}")
        s = store.proxy(data)

    u = [c for c in t]

    print(q)
    print(p)
    print(len(u))
    print(len(s))
