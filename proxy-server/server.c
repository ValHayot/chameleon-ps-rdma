#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <margo.h>
#include <mercury.h>
#include <mercury_macros.h>
#include "types.h"


// to handle process termination
// Doesn't actually work properly
// need to find a better alternative to cleaning up on the server side
margo_instance_id cur_mid;

void intHandler(int intrpt)
{
    margo_finalize(cur_mid);
}

static void set(hg_handle_t h);
static void get(hg_handle_t h);

DECLARE_MARGO_RPC_HANDLER(set)
DECLARE_MARGO_RPC_HANDLER(get)

int main(int argc, char** argv)
{
    signal(SIGINT, intHandler);

    margo_instance_id mid = margo_init("tcp", MARGO_SERVER_MODE, 0, 0);
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

        // write data to file
        FILE *fptr;

        if ((fptr = fopen(in.key, "wb+")) == NULL)
        {
            margo_error(mid, "could not open file %s for writing\n", in.key);
            out.ret = -1;
        }
        else
        {
            fwrite(val, in.size, 1, fptr);
            fclose(fptr);
        }
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

    margo_instance_id mid = margo_hg_handle_get_instance(h);

    const struct hg_info* info = margo_get_info(h);
    hg_addr_t client_addr = info->addr;

    ret = margo_get_input(h, &in);
    assert(ret == HG_SUCCESS);


    // read data from file

    if ((fptr = fopen(in.key, "r")) == NULL)
    {
        margo_error(mid, "could not open file %s for reading\n", in.key);
        out.ret = -1;
    }
    else
    {
        // get length of file
        fseek(fptr, 0, SEEK_END);
        long fsize = ftell(fptr);
        fseek(fptr, 0, SEEK_SET);

        val = malloc(fsize + 1);

        read_size = fread(val, fsize, 1, fptr);

        if (read_size > 0)
        {
            val[fsize] = 0;
            fclose(fptr);
            buf_size = fsize;

            ret = margo_bulk_create(mid, 1, (void*)&val, &buf_size,
                    HG_BULK_READ_ONLY, &local_bulk);
            assert(ret == HG_SUCCESS);

            ret = margo_bulk_transfer(mid, HG_BULK_PUSH, client_addr,
                    in.bulk, 0, local_bulk, 0, buf_size);
            assert(ret == HG_SUCCESS);

            out.ret = 0;
        }
        else 
        {
           // read error
           out.ret = -1;
        }
    }

    ret = margo_respond(h, &out);
    assert(ret == HG_SUCCESS);

    ret = margo_bulk_free(local_bulk);
    assert(ret == HG_SUCCESS);

    ret = margo_free_input(h, &in);
    assert(ret == HG_SUCCESS);

    ret = margo_destroy(h);
    assert(ret == HG_SUCCESS);

}

DEFINE_MARGO_RPC_HANDLER(set)
DEFINE_MARGO_RPC_HANDLER(get)
