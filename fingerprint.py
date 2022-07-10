from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List
import struct

from common import logger

import acoustid
import chromaprint

cache_path = Path('~/.cache/audups').expanduser()

@dataclass
class FingerprintResult:
  fingerprint: List[int]
  encoded_fp: bytes = None
  error: str = None


def set_globals(values):
  for k, v in values.items():
    globals()[k] = v


def pack_int32_array(l):
  return struct.pack('i' * len(l), *l)


def get_cached_path(filepath, sample_time):
  return cache_path / Path(filepath).relative_to('/').with_suffix(
    f'.chromaprint'
  )


def calculate_fingerprint(filepath, sample_time):
  try:
    with open(get_cached_path(filepath, sample_time), 'rb') as f:
      fingerprint, _ = chromaprint.decode_fingerprint(f.read())
      return FingerprintResult(fingerprint)
  except FileNotFoundError:
    pass

  duration, encoded_fp = acoustid.fingerprint_file(filepath, maxlength=sample_time)

  if float(duration) < sample_time:
    return FingerprintResult(None, error=f'Audio duration is too short ({duration}s < {sample_time}s)')

  fingerprint, _ = chromaprint.decode_fingerprint(encoded_fp)
  return FingerprintResult(fingerprint, encoded_fp=encoded_fp)


def _calculate_fingerprint(p):
  return p, calculate_fingerprint(p, sample_time)


def get_fingerprints(paths, sample_time, workers):
  files = []
  fingerprints = []
  logger.info(f'Fingerprinting {len(paths)} file(s)')

  g_vars = {
    'sample_time': sample_time
  }

  with ProcessPoolExecutor(
    max_workers=workers,
    initializer=set_globals,
    initargs=(g_vars,)
  ) as pool:
    for filepath, res in pool.map(_calculate_fingerprint, paths):
      if res.error is not None:
        logger.warn(f'Skipping "{filepath}": {res.error}')
        continue
      files.append(filepath)
      fingerprints.append(pack_int32_array(res.fingerprint))
      if res.encoded_fp:
        cache_file = get_cached_path(filepath, sample_time)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'wb') as f:
          f.write(res.encoded_fp)

  return files, fingerprints