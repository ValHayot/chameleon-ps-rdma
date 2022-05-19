#!/bin/bash

# source this file to setup environment for mochi-margo usage
# need to update to move relevant commands to ~/.bashrc


. $PWD/spack/share/spack/setup-env.sh
spack compiler find

spack repo add mochi-spack-packages
spack info mochi-margo
spack install mochi-margo ^libfabric fabrics=rxm,sockets,tcp,efa,mlx,mrail,rxd,shm,udp,verbs,xpmem,cxi

spack install redis
spack install hiredis

echo ". $PWD/spack/share/spack/setup-env.sh
spack load mochi-margo
spack load cmake
spack load redis
spack load hiredis

pkg-config --libs margo
pkg-config --libs hiredis" >> ~/.bashrc
