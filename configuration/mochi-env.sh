#!/bin/bash

# source this file to setup environment for mochi-margo usage
# need to update to move relevant commands to ~/.bashrc


. spack/share/spack/setup-env.sh
spack compiler find

spack repo add mochi-spack-packages
spack info mochi-margo
spack install mochi-margo ^libfabric fabrics=rxm,sockets,tcp,efa,mlx,mrail,rxd,shm,udp,verbs,xpmem,cxi
spack load mochi-margo
spack load cmake

spack install redis
spack install hiredis

pkg-config --libs margo
pkg-config --libs hiredis
