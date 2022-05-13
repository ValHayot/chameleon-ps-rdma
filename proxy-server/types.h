#ifndef PARAM_H
#define PARAM_H

#include <mercury.h>
#include <mercury_macros.h>
#include <mercury_proc_string.h>

MERCURY_GEN_PROC(push_in_t,
        ((hg_string_t)(key))\
        ((hg_bulk_t)(bulk)))

MERCURY_GEN_PROC(push_out_t, ((int32_t)(ret)))

#endif
