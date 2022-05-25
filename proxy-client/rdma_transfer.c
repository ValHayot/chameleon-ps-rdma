#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <assert.h>
#include <stdio.h>
#include <margo.h>
#include "types.h"

hg_addr_t server_addr;
margo_instance_id mid;

static PyObject *
rdma_set(PyObject *self, PyObject *args)
{
    char *key, *value;

    if (!PyArg_ParseTuple(args, "ss*", &key, &value))
        return NULL;

    rdma_in_t item;

    hg_string_t d[1] = { value };
    hg_bulk_t local_bulk;
    hg_size_t sizes[1] = { strlen(d[0]) };
    void *ptrs = { (void*)d };

    hg_id_t set_rpc_id = MARGO_REGISTER(mid, "set", rdma_in_t, rdma_out_t, NULL);
    margo_bulk_create(mid, 1, ptrs, sizes, HG_BULK_READ_ONLY, &local_bulk);

    item.key = key;
    item.size = sizes[0];
    item.bulk = local_bulk;

    double timeout = 5000;
    hg_handle_t h;
    margo_create(mid, server_addr, set_rpc_id, &h);
    margo_forward_timed(h, &item, timeout);

    rdma_out_t resp;
    margo_get_output(h, &resp);
    //margo_info(mid, "Got response: %d\n", resp.ret);

    margo_free_output(h, &resp);
    margo_destroy(h);

    margo_bulk_free(local_bulk);

    PyObject *val = PyBytes_FromStringAndSize(d[0], sizeof(d[0]));
    return val;
}

static PyObject *
rdma_get(PyObject *self, PyObject *args)
{
    char *key;
    size_t size;
    //PyObject *data = PyDict_New();

    if (!PyArg_ParseTuple(args, "sn", &key, &size))
        return NULL;

    rdma_in_t item;

    hg_string_t d[1] = { calloc(1, size) };
    hg_bulk_t local_bulk;
    hg_size_t sizes[1] = { size };
    void *ptrs = { (void*)d };
    
    hg_id_t get_rpc_id = MARGO_REGISTER(mid, "get", rdma_in_t, rdma_out_t, NULL);
    margo_bulk_create(mid, 1, ptrs, sizes, HG_BULK_WRITE_ONLY, &local_bulk);

    item.key = key;
    item.size = size;
    item.bulk = local_bulk;

    double timeout = 5000;
    hg_handle_t h;
    margo_create(mid, server_addr, get_rpc_id, &h);
    margo_forward_timed(h, &item, timeout);

    rdma_out_t resp;
    margo_get_output(h, &resp);
    //margo_info(mid, "Got response: %d %s %d\n", resp.ret, d[0], sizeof(d));

    margo_free_output(h, &resp);
    margo_destroy(h);

    margo_bulk_free(local_bulk);

    PyObject *val = PyBytes_FromString(d[0]);
    //PyDict_SetItemString(data, key, val);
    return val;
}

static PyObject*
rdma_connect(PyObject *self, PyObject *args)
{

    if (mid != NULL)
    {
        //hg_return_t ret;

        //ret = 
        return PyLong_FromLong(0);
        //margo_addr_free(mid, server_addr);
        //margo_finalize(mid);
    }

    char *addr;
    if (!PyArg_ParseTuple(args, "s", &addr))
        return NULL;


    hg_return_t ret;
    // verify that all options are correct
    mid = margo_init("tcp", MARGO_CLIENT_MODE, 1, 0);
    // let user provide log level
    margo_set_log_level(mid, MARGO_LOG_INFO);
    ret = margo_addr_lookup(mid, addr, &server_addr);

    return PyLong_FromLong(ret);

}


static PyObject*
rdma_close(PyObject *self, PyObject *args)
{

    hg_return_t ret;

    ret = margo_addr_free(mid, server_addr);
    margo_finalize(mid);
    return PyLong_FromLong(ret);

}

static PyMethodDef rdmaMethods[] = {
    {"set",  rdma_set, METH_VARARGS,
     "Transfer data to server"},
    {"get",  rdma_get, METH_VARARGS,
     "Receive data from server"},
    {"connect", rdma_connect, METH_VARARGS,
     "Connect to server"},
    {"disconnect", rdma_close, METH_VARARGS,
     "Terminate connection to server"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef rdmamodule = {
    PyModuleDef_HEAD_INIT,
    "rdma_transfer",   /* name of module */
    NULL, /* module documentation, may be NULL */
    -1,       /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
    rdmaMethods
};



PyMODINIT_FUNC
PyInit_rdma_transfer(void)
{
    return PyModule_Create(&rdmamodule);
}


int
main(int argc, char *argv[])
{
    wchar_t *program = Py_DecodeLocale(argv[0], NULL);
    if (program == NULL) {
        fprintf(stderr, "Fatal error: cannot decode argv[0]\n");
        exit(1);
    }

    /* Add a built-in module, before Py_Initialize */
    if (PyImport_AppendInittab("rdma_transfer", PyInit_rdma_transfer) == -1) {
        fprintf(stderr, "Error: could not extend in-built modules table\n");
        exit(1);
    }

    /* Pass argv[0] to the Python interpreter */
    Py_SetProgramName(program);

    /* Initialize the Python interpreter.  Required.
 *        If this step fails, it will be a fatal error. */
    Py_Initialize();

    /* Optionally import the module; alternatively,
 *        import can be deferred until the embedded script
 *               imports it. */
    PyObject *pmodule = PyImport_ImportModule("rdma_transfer");
    if (!pmodule) {
        PyErr_Print();
        fprintf(stderr, "Error: could not import module 'rdma_transfer'\n");
    }

    PyMem_RawFree(program);
    return 0;
}
