#define PY_SPy_ssize_t_CLEAN
#include <Python.h>

#define max(a,b)             \
({                           \
    __typeof__ (a) _a = (a); \
    __typeof__ (b) _b = (b); \
    _a > _b ? _a : _b;       \
})

#define min(a,b)             \
({                           \
    __typeof__ (a) _a = (a); \
    __typeof__ (b) _b = (b); \
    _a < _b ? _a : _b;       \
})

float correlate(
  uint32_t x[], uint32_t y[],
  Py_ssize_t size_x, Py_ssize_t size_y,
  int offset
) {
  Py_ssize_t xoff = 0, yoff = 0, offset_real = 0;

  if (offset > 0) {
    xoff = (Py_ssize_t)offset;
    offset_real = xoff;
  } else if (offset < 0) {
    yoff = (Py_ssize_t)(-offset);
    offset_real = yoff;
  }
  Py_ssize_t len = min(size_x - offset_real, size_y - offset_real);

  unsigned int error = 0;
  for (Py_ssize_t i = 0; i < len; i++) {
    error += __builtin_popcount(x[i + xoff] ^ y[i + yoff]);
  }
  return 1.f - (float)error / 32.f / (float)len;
}

static PyObject* cross_correlate(PyObject *self, PyObject *args)
{
  PyObject* bytes_x;
  PyObject* bytes_y;
  int max_offset;
  float threshold;

  if (!PyArg_ParseTuple(
    args, "SSif",
    &bytes_x, &bytes_y, &max_offset, &threshold
  )) {
    return NULL;
  }

  Py_ssize_t size_x = PyBytes_GET_SIZE(bytes_x) / sizeof(uint32_t);
  Py_ssize_t size_y = PyBytes_GET_SIZE(bytes_y) / sizeof(uint32_t);
  uint32_t* x = (uint32_t*)(PyBytes_AS_STRING(bytes_x));
  uint32_t* y = (uint32_t*)(PyBytes_AS_STRING(bytes_y));
  max_offset = abs(max_offset);

  if (max_offset >= size_x || max_offset >= size_y) {
    PyErr_SetString(PyExc_TypeError, "input arrays must be longer than offset");
    return NULL;
  }

  float best_corr = 0;
  int best_offset = 0;
  float corr;

  corr = correlate(x, y, size_x, size_y, 0);
  if (corr > best_corr) {
    if (corr >= threshold)
      return Py_BuildValue("fi", corr, 0);
    best_corr = corr;
  }

  for (int offset = 1; offset <= max_offset; offset++)
  {
    corr = correlate(x, y, size_x, size_y, offset);
    if (corr > best_corr) {
      if (corr >= threshold)
        return Py_BuildValue("fi", corr, offset);
      best_corr = corr;
      best_offset = offset;
    }

    corr = correlate(x, y, size_x, size_y, -offset);
    if (corr > best_corr) {
      if (corr >= threshold)
        return Py_BuildValue("fi", corr, -offset);
      best_corr = corr;
      best_offset = -offset;
    }
  }
  return Py_BuildValue("fi", best_corr, best_offset);
}

static PyMethodDef Methods[] = {
  {"cross_correlate",  cross_correlate, METH_VARARGS, "Calculates bitwise cross correlation of two chromaprints"},
  {NULL, NULL, 0, NULL}
};

static struct PyModuleDef Module = {
  PyModuleDef_HEAD_INIT,
  "correlate",   /* name of module */
  NULL, /* module documentation, may be NULL */
  -1,       /* size of per-interpreter state of the module,
                or -1 if the module keeps state in global variables. */
  Methods
};

PyMODINIT_FUNC PyInit_correlate(void)
{
  return PyModule_Create(&Module);
}