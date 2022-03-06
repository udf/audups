from dataclasses import dataclass
import itertools
from concurrent.futures import ThreadPoolExecutor
import subprocess
import json
from pathlib import Path
from typing import List

import common
from common import logger

cache_path = Path('fpcache')


@dataclass
class FingerprintResult:
  fingerprint: List[int]
  from_cache: bool = False
  error: str = None


def get_cached_path(filepath):
  return cache_path / Path(filepath).relative_to('/').with_suffix(
    f'.fpcalc{common.sample_time}'
  )


def calculate_fingerprint(filepath):
  try:
    with open(get_cached_path(filepath)) as f:
      return FingerprintResult(json.load(f), from_cache=True)
  except FileNotFoundError:
    pass

  p = subprocess.run(
    [
      'fpcalc',
      '-plain',
      '-raw',
      '-length',
      f'{common.sample_time}',
      filepath
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
  )

  if p.returncode != 0:
    return FingerprintResult(None, error=p.stderr.decode("utf-8").strip())

  fingerprint = [int(i) for i in p.stdout.decode('utf-8').strip().split(',')]
  return FingerprintResult(fingerprint)


def get_fingerprints(paths):
  files = []
  fingerprints = []
  logger.info(f'Fingerprinting {len(paths)} file(s)')

  with ThreadPoolExecutor(max_workers=common.n_workers) as pool:
    for filepath, res in pool.map(
      lambda p: (p, calculate_fingerprint(p)),
      paths
    ):
      if res.error:
        logger.warn(f'Skipping "{filepath}": {res.error}')
        continue
      files.append(filepath)
      fingerprints.append(res.fingerprint)
      if not res.from_cache:
        cache_file = get_cached_path(filepath)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w') as f:
          json.dump(res.fingerprint, f)

  return files, fingerprints