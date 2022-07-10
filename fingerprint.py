from dataclasses import dataclass
import itertools
from concurrent.futures import ThreadPoolExecutor
import subprocess
import json
from pathlib import Path
from typing import List
import struct

import common
from common import logger

import ffmpeg

cache_path = Path('fpcache')


@dataclass
class FingerprintResult:
  fingerprint: List[int]
  from_cache: bool = False
  error: str = None


def pack_int32_array(l):
  return struct.pack('I' * len(l), *l)


def get_cached_path(filepath, sample_time):
  return cache_path / Path(filepath).relative_to('/').with_suffix(
    f'.fpcalc{sample_time}'
  )


def calculate_fingerprint(filepath, sample_time):
  try:
    with open(get_cached_path(filepath, sample_time)) as f:
      return FingerprintResult(json.load(f), from_cache=True)
  except (FileNotFoundError, json.JSONDecodeError):
    pass

  length = 0
  probe = ffmpeg.probe(filepath)
  for stream in probe['streams']:
    if stream['codec_type'] == 'audio':
      length = stream['duration']
      break

  if float(length) < sample_time:
    return FingerprintResult(None, error=f'First audio stream is too short ({length}s < {sample_time}s)')

  p = subprocess.run(
    [
      'fpcalc',
      '-plain',
      '-raw',
      '-length',
      f'{sample_time}',
      filepath
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
  )

  if p.returncode != 0:
    return FingerprintResult(None, error=p.stderr.decode("utf-8").strip())

  fingerprint = [int(i) for i in p.stdout.decode('utf-8').strip().split(',')]
  return FingerprintResult(fingerprint)


def get_fingerprints(paths, sample_time, workers):
  files = []
  fingerprints = []
  logger.info(f'Fingerprinting {len(paths)} file(s)')

  with ThreadPoolExecutor(max_workers=workers) as pool:
    for filepath, res in pool.map(
      lambda p: (p, calculate_fingerprint(p, sample_time=sample_time)),
      paths
    ):
      if res.error is not None:
        logger.warn(f'Skipping "{filepath}": {res.error}')
        continue
      files.append(filepath)
      fingerprints.append(pack_int32_array(res.fingerprint))
      if not res.from_cache:
        cache_file = get_cached_path(filepath, sample_time)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w') as f:
          json.dump(res.fingerprint, f)

  return files, fingerprints