from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List
import struct

from .common import logger, dynamic_tqdm

import audioread
import acoustid
import chromaprint

cache_path = Path('~/.cache/audups').expanduser()

@dataclass
class FingerprintResult:
  fingerprint: List[int]
  encoded_fp: bytes = None
  error: str = None


def _set_globals(values):
  for k, v in values.items():
    globals()[k] = v


def _pack_int32_array(l):
  return struct.pack('i' * len(l), *l)


def _pack_uint32_array(l):
  return struct.pack('I' * len(l), *l)


def _get_cached_path(filepath, sample_time):
  return cache_path / Path(filepath).resolve().relative_to('/').with_suffix(
    f'.chromaprint'
  )


# force ffdec because of GStreamer bug with mp3
# https://github.com/beetbox/audioread/issues/111
def _fingerprint_file_audioread_ffdec(path, maxlength):
  """Fingerprint a file by using audioread and chromaprint."""
  try:
    with audioread.audio_open(path, backends=(audioread.ffdec.FFmpegAudioFile,)) as f:
      if f.channels > 2:
        # TODO: make own reader that merges channels in ffmpeg
        raise RuntimeError('fixme: too many channels')
      duration = f.duration
      fp = acoustid.fingerprint(f.samplerate, f.channels, iter(f), maxlength)
  except audioread.DecodeError:
    raise acoustid.FingerprintGenerationError("audio could not be decoded")
  return duration, fp


def calculate_fingerprint(filepath, sample_time):
  fp_path = _get_cached_path(filepath, sample_time)
  if not Path(filepath).exists:
    if fp_path.exists():
      logger.info(f'Removing old fingerprint {fp_path}')
      fp_path.unlink()
    return FingerprintResult(None, error='file not found')
  try:
    with open(fp_path, 'rb') as f:
      fingerprint, _ = chromaprint.decode_fingerprint(f.read())
      return FingerprintResult(fingerprint)
  except FileNotFoundError:
    pass

  try:
    duration, encoded_fp = _fingerprint_file_audioread_ffdec(filepath, maxlength=sample_time)
  except Exception as e:
    return FingerprintResult(None, error=str(e))

  fingerprint, _ = chromaprint.decode_fingerprint(encoded_fp)
  return FingerprintResult(fingerprint, encoded_fp=encoded_fp)


def _calculate_fingerprint(p):
  return p, calculate_fingerprint(p, sample_time)


def get_fingerprints(paths, sample_time, workers, min_fp_len):
  files = []
  fingerprints = []
  logger.info(f'Fingerprinting {len(paths)} file(s)')

  g_vars = {
    'sample_time': sample_time
  }

  with (
    ProcessPoolExecutor(
      max_workers=workers,
      initializer=_set_globals,
      initargs=(g_vars,)
    ) as pool,
    dynamic_tqdm(total=len(paths), unit=' files', dynamic_ncols=True) as progress
  ):
    for filepath, res in pool.map(_calculate_fingerprint, paths, chunksize=8):
      if progress:
        progress.update(1)
      if res.error is not None:
        logger.warn(f'Skipping "{filepath}": {res.error}')
        continue
      if len(res.fingerprint) <= min_fp_len:
        logger.warn(
          f'Skipping "{filepath}": fingerprint too short ({len(res.fingerprint)}/{min_fp_len})'
        )
        continue
      files.append(filepath)
      fingerprints.append(_FP_PACK_FUNC(res.fingerprint))
      if res.encoded_fp:
        cache_file = _get_cached_path(filepath, sample_time)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'wb') as f:
          f.write(res.encoded_fp)

  return files, fingerprints


# pyacoustid <= 1.2.2 returns signed ints from chromaprint.decode_fingerprint
# (there is no __version__ attribute present, so decode a sample to see if this is the case)
def _get_fp_pack_func():
  encoded_fp = b'AQAAO1GWJFGbRdDMJ0R-1JKMZ0a9qeBE4ZXwH7kCLVxmnMkFMvpRHc0YvjgeUQ4a9_hhwk_AlMN1HLqDJ8qFqwu0FLWOPguaN_j0Bt2UB1uePJieiBL0B9XBRNPxqROuTAz6TEdz6Cv-4zqeH9oDVzeuiGi-gT_opUdz4RkDs8rBNSRhNehH_ABBmJCGAAeQERKQo5BBwEAiDDACASAIEMgwAZASiCgiCGBCEAMRUYBCZJUC'
  decoded, _ = chromaprint.decode_fingerprint(encoded_fp)
  if min(decoded) < 0:
    return _pack_int32_array
  return _pack_uint32_array


_FP_PACK_FUNC = _get_fp_pack_func()