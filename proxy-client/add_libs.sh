#!/bin/bash

libs=$(pkgconf --libs margo)

# get the library paths
margo=$(echo $libs | grep -Ewo "L\S*margo\S*")
mercury=$(echo $libs | grep -Ewo "L\S*mercury\S*")
abt=$(echo $libs | grep -Ewo "L\S*argobots\S*")

# strip the 'L'
margo=${margo:1}
mercury=${mercury:1}
abt=${abt:1}

echo ${margo}
echo ${mercury}
echo ${abt}

export CPATH=$CPATH:$(dirname ${margo})/include:$(dirname ${mercury})/include:$(dirname ${abt})/include
export LIBRARY_PATH=${LIBRARY_PATH}:${margo}:${mercury}:${abt}
