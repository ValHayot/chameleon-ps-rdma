#!/bin/bash

globus_tar=globusconnectpersonal-latest.tgz
cd ~
wget https://downloads.globus.org/globus-connect-personal/linux/stable/${globus_tar}
tar xzf ${globus_tar}
rm -r ${globus_tar}*

connect_fldr=$(echo globusconnectpersonal-*)
echo ${connect_fldr}
cd ${connect_fldr}
./globusconnectpersonal -setup
./globusconnectpersonal -start &
