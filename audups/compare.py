import itertools
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from dataclasses import dataclass
import sys

from .fingerprint import get_fingerprints
from .common import logger, dynamic_tqdm
from .pool_lazy_map import lazy_map
from . import correlate


@dataclass
class DuplicateResult:
  a: Path
  b: Path
  similarity: float


def _walk_files(path):
  if os.path.isfile(path):
    yield Path(path)
    return
  for root, dirs, files in os.walk(path):
    root = Path(root)
    for file in files:
      f: Path = root / file
      yield f


def list_music(path):
  logger.info(f'Collecting files from {path}')
  return [
    p for p in _walk_files(path)
    if p.suffix.lower() in {'.opus', '.flac', '.mp3', '.m4a', '.ogg'}
  ]


def _triangle(n):
  return n * (n - 1) // 2


def _do_comparison(v):
  ia, ib = v
  res = correlate.compare_fp(
    fingerprints_a[ia], fingerprints_b[ib], max_offset
  )
  return (ia, ib), res


def _set_globals(values):
  for k, v in values.items():
    globals()[k] = v


def _process_results(files_a, files_b, results, threshold):
  for (ia, ib), similarity in results:
    if similarity < threshold:
      continue
    a, b = files_a[ia], files_b[ib]
    yield DuplicateResult(a, b, similarity)


def compare_filelists(
  files_a, files_b=None,
  threshold=0.9, max_offset=80, sample_time=90,
  fp_workers=8, workers=32
):
  if files_b is None:
    files_a, fingerprints_a = get_fingerprints(
      files_a, sample_time=sample_time, workers=fp_workers, min_fp_len=max_offset
    )
    files_b, fingerprints_b = files_a, fingerprints_a
    job_count = _triangle(len(files_a))
    job_param_gen = (
      (ia, ib)
      for (ia, a), (ib, b) in
      itertools.combinations(enumerate(files_a), 2)
    )
    logger.info(f'Calculated {len(files_a)} fingerprints')
  else:
    files_a, fingerprints_a = get_fingerprints(
      files_a, sample_time=sample_time, workers=fp_workers, min_fp_len=max_offset
    )
    files_b, fingerprints_b = get_fingerprints(
      files_b, sample_time=sample_time, workers=fp_workers, min_fp_len=max_offset
    )
    job_count = len(files_a) * len(files_b)
    job_param_gen = (
      (ia, ib)
      for (ia, a), (ib, b) in
      itertools.product(enumerate(files_a), enumerate(files_b))
    )
    logger.info(f'Calculated {len(files_a) + len(files_b)} fingerprints')

  logger.info(f'Doing {job_count} comparison(s)')

  g_vars = {
    'fingerprints_a': fingerprints_a,
    'fingerprints_b': fingerprints_b,
    'max_offset': max_offset
  }

  chunksize = 32768
  with (
    ProcessPoolExecutor(
      max_workers=workers,
      initializer=_set_globals,
      initargs=(g_vars,)
    ) as pool,
    dynamic_tqdm(total=job_count, unit=' comps', dynamic_ncols=True) as progress
  ):
    for fut in lazy_map(pool, _do_comparison, job_param_gen, chunksize=chunksize):
      try:
        res = fut.result()
      except:
        logger.exception('task exception')
        progress.update(chunksize)
        continue
      progress.update(len(res))
      yield from _process_results(files_a, files_b, res, threshold)


def compare_paths(
  paths_a, paths_b=None,
  threshold=0.9, max_offset=80, sample_time=90,
  fp_workers=8, workers=32
):
  files_a = []
  files_b = []
  for path in paths_a:
    files_a.extend(list_music(path))
  if paths_b:
    for path in paths_b:
      files_b.extend(list_music(path))

  return compare_filelists(
    files_a,
    files_b or None,
    threshold=threshold,
    max_offset=max_offset,
    sample_time=sample_time,
    fp_workers=fp_workers,
    workers=workers
  )