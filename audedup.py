import itertools
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from dataclasses import dataclass

import common
import fingerprint
from common import logger, n_workers
from correlation import correlate
from pool_lazy_map import lazy_map


fingerprints_a = []
fingerprints_b = []


@dataclass
class DuplicateResult:
  a: Path
  b: Path
  similarity: float
  # TODO: convert to seconds?
  offset: int


def walk_files(path):
  for root, dirs, files in os.walk(path):
    root = Path(root)
    for file in files:
      f: Path = root / file
      yield f


def list_music(path):
  logger.info(f'Collecting files from {path}')
  return [
    p for p in walk_files(path)
    if p.suffix.lower() in {'.opus', '.flac', '.mp3', '.m4a', '.ogg'}
  ]


def triangle(n):
  return n * (n - 1) // 2


def do_comparison(v):
  ia, ib = v
  return (ia, ib), correlate(fingerprints_a[ia], fingerprints_b[ib])


def process_results(files_a, files_b, results):
  for (ia, ib), (similarity, offset) in results:
    if similarity < common.threshold:
      continue
    a, b = files_a[ia], files_b[ib]
    yield DuplicateResult(a, b, similarity, offset)


def compare_fingerprints(files_a, files_b=None):
  #TODO: nonlocal
  global fingerprints_a, fingerprints_b

  if files_b is None:
    files_a, fingerprints_a = fingerprint.get_fingerprints(files_a)
    files_b, fingerprints_b = files_a, fingerprints_a
    job_count = triangle(len(files_a))
    job_param_gen = (
      (ia, ib)
      for (ia, a), (ib, b) in
      itertools.combinations(enumerate(files_a), 2)
    )
    logger.info(f'Calculated {len(files_a)} fingerprints')
  else:
    files_a, fingerprints_a = fingerprint.get_fingerprints(files_a)
    files_b, fingerprints_b = fingerprint.get_fingerprints(files_b)
    job_count = len(files_a) * len(files_b)
    job_param_gen = (
      (ia, ib)
      for (ia, a), (ib, b) in
      itertools.product(enumerate(files_a), enumerate(files_b))
    )
    logger.info(f'Calculated {len(files_a) + len(files_b)} fingerprints')

  logger.info(f'Doing {job_count} comparison(s)')

  chunksize = 4096
  # TODO: progress
  progress = 0
  with ProcessPoolExecutor(max_workers=n_workers) as pool:
    for fut in lazy_map(pool, do_comparison, job_param_gen, chunksize=chunksize):
      try:
        res = fut.result()
      except:
        logger.exception('task exception')
        progress += chunksize
        continue
      progress += len(res)
      print(f'{progress}/{job_count}')
      yield from process_results(files_a, files_b, res)


def compare_dirs(dir_a, dir_b=None):
  return compare_fingerprints(
    list_music(dir_a),
    list_music(dir_b) if dir_b is not None else None
  )