#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <margo.h>
#include <mercury.h>
#include <mercury_macros.h>
#include <hiredis.h>
#include "types.h"


// to handle process termination
// Doesn't actually work properly
// need to find a better alternative to cleaning up on the server side
margo_instance_id cur_mid;
redisContext *c;

void intHandler(int intrpt)
{
    redisFree(c);
    margo_finalize(cur_mid);
}

static void set(hg_handle_t h);
static void get(hg_handle_t h);

DECLARE_MARGO_RPC_HANDLER(set)
DECLARE_MARGO_RPC_HANDLER(get)

int main(int argc, char** argv)
{
    char* rport = argv[1];
    char* mochi_host = argv[2];
    char* mochi_port = argv[3];

    char mochi_addr[1024] = "tcp://";

    strcat(mochi_addr, mochi_host);
    strcat(mochi_addr, ":");
    strcat(mochi_addr, mochi_port);
   
    signal(SIGINT, intHandler);
    int redis_port = atoi(rport);

    // create redis context
    c = redisConnect("127.0.0.1", redis_port);
    if (c == NULL || c->err) {
        if (c) {
            printf("Error: %s port id: %d\n", c->errstr, redis_port);
            // handle error
            exit(0);
        } else {
            printf("Can't allocate redis context\n");
        }
    }

    // initialize margo instance
    margo_instance_id mid = margo_init(mochi_addr, MARGO_SERVER_MODE, 0, 0);
    assert(mid);
    margo_set_log_level(mid, MARGO_LOG_INFO);

    hg_addr_t my_address;
    margo_addr_self(mid, &my_address);
    char addr_str[128];
    size_t addr_str_size = 128;
    margo_addr_to_string(mid, addr_str, &addr_str_size, my_address);
    margo_addr_free(mid,my_address);

    margo_info(mid, "Server running at address %s\n", addr_str);

    MARGO_REGISTER(mid, "set", rdma_in_t, rdma_out_t, set);
    MARGO_REGISTER(mid, "get", rdma_in_t, rdma_out_t, get);

    cur_mid = mid;
    margo_wait_for_finalize(mid);

    return 0;
}

static void set(hg_handle_t h)
{

    hg_return_t ret;

    rdma_in_t in;
    rdma_out_t out;
    hg_bulk_t local_bulk;
    hg_string_t* val;

    redisReply *reply;

    margo_instance_id mid = margo_hg_handle_get_instance(h);

    const struct hg_info* info = margo_get_info(h);
    hg_addr_t client_addr = info->addr;

    ret = margo_get_input(h, &in);
    assert(ret == HG_SUCCESS);

    val = (hg_string_t*)malloc(in.size);
    if(val)
    {
        hg_size_t buf_size = in.size;

        ret = margo_bulk_create(mid, 1, (void**)&val, &buf_size,
                 HG_BULK_WRITE_ONLY, &local_bulk);
        assert(ret == HG_SUCCESS);

        ret = margo_bulk_transfer(mid, HG_BULK_PULL, client_addr,
                in.bulk, 0, local_bulk, 0, buf_size);
        assert(ret == HG_SUCCESS);

        out.ret = 0;

        //margo_info(mid, "obtained key %s and value %s\n", in.key, val);

        // store key-value pair in redis
        reply = redisCommand(c, "SET key:%s %b", in.key, val, (size_t)in.size);
        margo_debug(mid, "SET (binary API): %s\n", reply->str);
    }
   

    ret = margo_respond(h, &out);
    assert(ret == HG_SUCCESS);

    ret = margo_bulk_free(local_bulk);
    assert(ret == HG_SUCCESS);

    ret = margo_free_input(h, &in);
    assert(ret == HG_SUCCESS);

    ret = margo_destroy(h);
    assert(ret == HG_SUCCESS);

    free(val);
    freeReplyObject(reply);
}

static void get(hg_handle_t h)
{
    hg_return_t ret;

    rdma_in_t in;
    rdma_out_t out;
    hg_bulk_t local_bulk;
    hg_string_t val;
    hg_size_t buf_size;
    
    FILE *fptr;
    size_t read_size;

    redisReply *reply;

    margo_instance_id mid = margo_hg_handle_get_instance(h);

    const struct hg_info* info = margo_get_info(h);
    hg_addr_t client_addr = info->addr;

    ret = margo_get_input(h, &in);
    assert(ret == HG_SUCCESS);


    // get data from redis
    reply = redisCommand(c, "GET key:%s", in.key);

    margo_debug(mid, "GET %s\n", in.key);

    val = reply->str;
    buf_size = strlen(reply->str);

    ret = margo_bulk_create(mid, 1, (void*)&val, &buf_size,
	    HG_BULK_READ_ONLY, &local_bulk);
    assert(ret == HG_SUCCESS);

    ret = margo_bulk_transfer(mid, HG_BULK_PUSH, client_addr,
	    in.bulk, 0, local_bulk, 0, buf_size);
    assert(ret == HG_SUCCESS);

    out.ret = 0;

    ret = margo_respond(h, &out);
    assert(ret == HG_SUCCESS);

    ret = margo_bulk_free(local_bulk);
    assert(ret == HG_SUCCESS);

    ret = margo_free_input(h, &in);
    assert(ret == HG_SUCCESS);

    ret = margo_destroy(h);
    assert(ret == HG_SUCCESS);

    freeReplyObject(reply);

}

DEFINE_MARGO_RPC_HANDLER(set)
DEFINE_MARGO_RPC_HANDLER(get)
