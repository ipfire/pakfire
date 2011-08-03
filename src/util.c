
#include <Python.h>

#include "util.h"

PyObject *version_compare(PyObject *self, PyObject *args) {
	Pool *pool;
	const char *evr1, *evr2;

	if (!PyArg_ParseTuple(args, "Oss", &pool, &evr1, &evr2)) {
		/* XXX raise exception */
		return NULL;
	}

	int ret = pool_evrcmp_str(pool, evr1, evr2, EVRCMP_COMPARE);

	return Py_BuildValue("i", ret);
}
