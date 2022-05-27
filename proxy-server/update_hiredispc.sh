#!/bin/bash

hiredispc=$(pkgconf hiredis --path)
prefix=$(dirname $(dirname $(dirname ${hiredispc})))

prefix_str=$(sed 's/\//\\\//g' <<< ${prefix})
echo ${prefix_str}
sed_str="s/\/usr\/local/${prefix_str}/g"
echo ${sed_str}
sed -i -r "${sed_str}" "${hiredispc}"
