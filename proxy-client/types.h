#ifndef PARAM_H 
#define PARAM_H 
 
#include <mercury.h> 
#include <mercury_macros.h> 
#include <mercury_proc_string.h> 
 
MERCURY_GEN_PROC(rdma_in_t, 
        ((hg_string_t)(key))\
        ((int32_t)(size))\
        ((hg_bulk_t)(bulk)))

MERCURY_GEN_PROC(rdma_out_t, ((int32_t)(ret))) 
 
#endif
