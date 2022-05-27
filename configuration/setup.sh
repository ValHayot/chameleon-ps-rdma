#!/bin/bash

sudo yum update -y
sudo yum install -y vim

## setup infiniband
sudo yum -y groupinstall "Infiniband Support"
sudo yum -y install infiniband-diags perftest gperf

sudo systemctl start rdma
sudo systemctl enable rdma

ibconf="/etc/sysconfig/network-scripts/ifcfg-ib0"

sudo sed -i 's/dhcp/static/g' ${ibconf} 

if [[ $(grep -i netmask ${ibconf})  == "" ]]
then
	sudo echo "NETMASK=255.255.255.0" | sudo tee -a ${ibconf}
fi

endip=$( ifconfig eth0 | grep "inet " | awk '{print $2}' | cut -d. -f 3-4 )
ip=172.16.${endip}

if [[ $(grep -i ipaddr ${ibconf})  == "" ]]
then
	sudo echo "IPADDR=${ip}" | sudo tee -a ${ibconf}
fi

sudo ifdown ib0
sudo ifup ib0

# install spack
git clone -c feature.manyFiles=true https://github.com/spack/spack.git
# install mochi/margo
git clone https://github.com/mochi-hpc/mochi-spack-packages.git

# upgrade GCC
sudo yum group install "Development Tools" -y
sudo yum install centos-release-scl -y
sudo yum clean all -y
sudo yum install devtoolset-11-* -y
scl enable devtoolset-11 bash

# install keydb
$ wget https://download.keydb.dev/pkg/open_source/rpm/centos7/x86_64/keydb-latest-1.el7.x86_64.rpm
$ sudo yum install ./keydb-latest-1.el7.x86_64.rpm
