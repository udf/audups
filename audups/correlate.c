// Ported from https://github.com/acoustid/pg_acoustid/blob/102f3c870c6157704694c2ddbad3ae8ab2c7de91/acoustid_compare.c
#define PY_SPy_ssize_t_CLEAN
#include <Python.h>

#define Max(a,b)             \
({                           \
    __typeof__ (a) _a = (a); \
    __typeof__ (b) _b = (b); \
    _a > _b ? _a : _b;       \
})

#define Min(a,b)             \
({                           \
    __typeof__ (a) _a = (a); \
    __typeof__ (b) _b = (b); \
    _a < _b ? _a : _b;       \
})

#define MATCH_BITS 14
#define MATCH_MASK ((1 << MATCH_BITS) - 1)
#define MATCH_STRIP(x) ((uint32_t)(x) >> (32 - MATCH_BITS))

#define UNIQ_BITS 16
#define UNIQ_MASK ((1 << MATCH_BITS) - 1)
#define UNIQ_STRIP(x) ((uint32_t)(x) >> (32 - MATCH_BITS))

static float match_fingerprints2(uint32_t *a, Py_ssize_t asize, uint32_t *b, Py_ssize_t bsize, int maxoffset)
{
  int i, topcount, topoffset, size, biterror, minsize, auniq = 0, buniq = 0;
  int numcounts = asize + bsize + 1;
  unsigned short *counts = calloc(numcounts, sizeof(unsigned short));
  uint8_t *seen;
  uint16_t *aoffsets, *boffsets;
  uint64_t *adata, *bdata;
  float score, diversity;

  aoffsets = calloc((MATCH_MASK + 1) * 2, sizeof(uint16_t));
  boffsets = aoffsets + MATCH_MASK + 1;
  seen = (uint8_t *)aoffsets;

  for (i = 0; i < asize; i++) {
    aoffsets[MATCH_STRIP(a[i])] = i;
  }
  for (i = 0; i < bsize; i++) {
    boffsets[MATCH_STRIP(b[i])] = i;
  }

  topcount = 0;
  topoffset = 0;
  for (i = 0; i < MATCH_MASK; i++) {
    if (aoffsets[i] && boffsets[i]) {
      int offset = aoffsets[i] - boffsets[i];
      if (maxoffset == 0 || (-maxoffset <= offset && offset <= maxoffset)) {
        offset += bsize;
        counts[offset]++;
        if (counts[offset] > topcount) {
          topcount = counts[offset];
          topoffset = offset;
        }
      }
    }
  }

  topoffset -= bsize;

  minsize = Min(asize, bsize) & ~1;
  if (topoffset < 0) {
    b -= topoffset;
    bsize = Max(0, bsize + topoffset);
  }
  else {
    a += topoffset;
    asize = Max(0, asize - topoffset);
  }

  size = Min(asize, bsize) / 2;
  if (!size || !minsize) {
    score = 0.0;
    goto exit;
  }

  memset(seen, 0, UNIQ_MASK);
  for (i = 0; i < asize; i++) {
    int key = UNIQ_STRIP(a[i]);
    if (!seen[key]) {
      auniq++;
      seen[key] = 1;
    }
  }

  memset(seen, 0, UNIQ_MASK);
  for (i = 0; i < bsize; i++) {
    int key = UNIQ_STRIP(b[i]);
    if (!seen[key]) {
      buniq++;
      seen[key] = 1;
    }
  }

  diversity = Min(
    Min(1.0, (float)(auniq + 10) / asize + 0.5),
    Min(1.0, (float)(buniq + 10) / bsize + 0.5)
  );

  if (topcount < Max(auniq, buniq) * 0.02) {
    score = 0.0;
    goto exit;
  }

  adata = (uint64_t *)a;
  bdata = (uint64_t *)b;
  biterror = 0;
  for (i = 0; i < size; i++, adata++, bdata++) {
    biterror += __builtin_popcountl(*adata ^ *bdata);
  }
  score = (size * 2.0 / minsize) * (1.0 - 2.0 * (float)biterror / (64 * size));
  if (score < 0.0) {
    score = 0.0;
  }
  if (diversity < 1.0) {
    float newscore = pow(score, 8.0 - 7.0 * diversity);
    score = newscore;
  }

exit:
  free(aoffsets);
  free(counts);
  return score;
}

static PyObject* compare_fp(PyObject *self, PyObject *args)
{
  PyObject* bytes_x;
  PyObject* bytes_y;
  int max_offset;

  if (!PyArg_ParseTuple(
    args, "SSi",
    &bytes_x, &bytes_y, &max_offset
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

  float similarity = match_fingerprints2(x, size_x, y, size_y, max_offset);

  return Py_BuildValue("f", similarity);
}

static PyMethodDef Methods[] = {
  {"compare_fp", compare_fp, METH_VARARGS, "Calculates similarity of two chromaprints"},
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