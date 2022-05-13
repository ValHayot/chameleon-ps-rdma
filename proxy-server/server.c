#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <margo.h>
#include <mercury.h>
#include <mercury_macros.h>
#include "types.h"

static const int TOTAL_RPCS = 4;
static int num_rpcs = 0;

typedef struct {
    char* key;
    hg_bulk_t value;
} item;

item* stored_items;

item* linear_search(item* items, size_t size, const char* key) {
    for (size_t i=0; i<size; i++) {
        if (strcmp(items[i].key, key) == 0) {
            return &items[i];
        }
    }
    return NULL;
}


static void push(hg_handle_t h);
//static void pull(hg_handle_t h);

DECLARE_MARGO_RPC_HANDLER(push)
//DECLARE_MARGO_RPC_HANDLER(pull)

int main(int argc, char** argv)
{
    stored_items = calloc(2, sizeof(item));
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

    MARGO_REGISTER(mid, "push", push_in_t, push_out_t, push);
    //MARGO_REGISTER(mid, "pull", pull_in_t, push_out_t, pull);

    margo_wait_for_finalize(mid);
    free(stored_items);

    return 0;
}

static void push(hg_handle_t h)
{
    hg_return_t ret;
    num_rpcs += 1;

    push_in_t in;
    push_out_t out;
    hg_bulk_t local_bulk;

    margo_instance_id mid = margo_hg_handle_get_instance(h);

    const struct hg_info* info = margo_get_info(h);
    hg_addr_t client_addr = info->addr;

    ret = margo_get_input(h, &in);
    assert(ret == HG_SUCCESS);

    hg_size_t buf_size = sizeof(stored_items);

    ret = margo_bulk_create(mid, 1, (void**)&stored_items, &buf_size,
            HG_BULK_WRITE_ONLY, &local_bulk);
    assert(ret == HG_SUCCESS);

    ret = margo_bulk_transfer(mid, HG_BULK_PULL, client_addr,
            in.bulk, 0, local_bulk, 0, buf_size);
    assert(ret == HG_SUCCESS);

    out.ret = 0;

    stored_items[0].key = in.key;
    stored_items[0].value = in.bulk;

    margo_info(mid, "obtained key %s with value %s\n", in.key, in.bulk);

    ret = margo_respond(h, &out);
    assert(ret == HG_SUCCESS);

    ret = margo_bulk_free(local_bulk);
    assert(ret == HG_SUCCESS);

    ret = margo_free_input(h, &in);
    assert(ret == HG_SUCCESS);

    ret = margo_destroy(h);
    assert(ret == HG_SUCCESS);

    if(num_rpcs == TOTAL_RPCS) {
        margo_finalize(mid);
    }
}
DEFINE_MARGO_RPC_HANDLER(push)
//DEFINE_MARGO_RPC_HANDLER(pull)
