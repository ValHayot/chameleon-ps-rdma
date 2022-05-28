#!/bin/bash

# store ip&ports
localip=127.0.0.1
remoteip=172.16.3.222 # will vary with different nodes
redis_port=6379
keydb_port=1234
mochi_port=45839
endpoints=endpoints.json
gcp=~/globusconnectpersonal-3.1.6/globusconnectpersonal
mochi=~/chameleon-ps-rdma/proxy-server/margo_server
load_spack="source ~/.mochiconf &> /dev/null"
connect_remote="ssh ${remoteip}"

reps=10
filestore=~/store

script_prefix="python benchmark.py --reps=${reps} --logfile "

local_bench() {
	logfile="local.log"
	rm ${logfile}
	echo -e "**Running LocalStore Benchmark**\n"
	${script_prefix} ${logfile} local

	echo -e "\n\n**Running FileStore local Benchmark**\n"
	mkdir ${filestore} # create store location
	${script_prefix} ${logfile} file ${filestore}
	rm -r ${filestore} # cleanup

	echo -e "\n\n**Running local RedisStore Benchmark**\n"
	redis-server --port ${redis_port} --daemonize yes
	sleep 15 # allow time for data load
	${script_prefix} ${logfile} redis ${localip} ${redis_port}
	redis-cli -p ${redis_port} FLUSHALL # clean the store
	redis-cli -p ${redis_port} SHUTDOWN # stop server

	echo -e "\n\n**Running local KeyDB Benchmark**\n"
	keydb-server --port ${keydb_port} --daemonize yes
	sleep 15 # allow time for data load
	${script_prefix} ${logfile} keydb ${localip} ${keydb_port}
	keydb-cli -h ${localip} -p ${keydb_port} FLUSHALL # clean the store
	keydb-cli -h ${localip} -p ${keydb_port} SHUTDOWN # stop server
}

remote_bench() {
	logfile="remote.log"
	rm ${logfile}

	echo -e "**Running remote RedisStore Benchmark**\n"
	${connect_remote} "${load_spack} && redis-server --port ${redis_port} --daemonize yes --protected-mode no"
	sleep 15 # allow time for data load
	${script_prefix} ${logfile} redis ${remoteip} ${redis_port}
	${connect_remote} "${load_spack} && redis-cli -p ${redis_port} FLUSHALL" # clean the store
	${connect_remote} "${load_spack} && redis-cli -p ${redis_port} SHUTDOWN" # stop server

	echo -e "\n\n**Running remote KeyDB Benchmark**\n"
	${connect_remote} "keydb-server --port ${keydb_port} --daemonize yes --protected-mode no"
	sleep 15 # allow time for data load
	${script_prefix} ${logfile} keydb ${remoteip} ${keydb_port}
	keydb-cli -h ${remoteip} -p ${keydb_port} FLUSHALL # clean the store
	keydb-cli -h ${remoteip} -p ${keydb_port} SHUTDOWN # stop server


	echo -e "\n\n**Running Globus Benchmark**\n"
	# create dir
        mkdir ${filestore}
        ${connect_remote} "mkdir ${filestore}"

	# start globus endpoint
	${gcp} -start &
	${connect_remote} ${gcp} -start &
	
	# run script
        ${script_prefix} ${logfile} globus ${endpoints}

	# stop globus endpoint
	${gcp} -stop
	${connect_remote} ${gcp} -stop

	# clean up endpoint dirs
        rm -r ${filestore}
	ssh ${remoteip} "rm -r ${filestore}"
        
	echo -e "\n\n**Running Mochi Benchmark\n"
	${connect_remote} "${load_spack} && redis-server --port ${redis_port} --daemonize yes"
	${connect_remote} "${mochi} ${redis_port} ${remoteip} ${mochi_port} &> outputs.log &"
        sleep 15
	${script_prefix} ${logfile} mochi "ofi+tcp;ofi_rxm://${remoteip}:${mochi_port}"
	${connect_remote} "pkill -f margo_server"

	${connect_remote} "${load_spack} && redis-cli -p ${redis_port} FLUSHALL" # clean the store
	${connect_remote} "${load_spack} && redis-cli -p ${redis_port} SHUTDOWN" # stop server

}

local_bench
remote_bench
