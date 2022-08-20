import argparse
import contextlib
import dataclasses
import json
import logging
import os
import sys

from tqdm.contrib import DummyTqdmFile

from .compare import compare_paths

__version__ = '0.1'


@contextlib.contextmanager
def _std_out_err_redirect_tqdm():
    orig_out_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = map(DummyTqdmFile, orig_out_err)
        yield orig_out_err[0]
    # Relay exceptions
    except Exception as exc:
        raise exc
    # Always restore sys.stdout/err if necessary
    finally:
        sys.stdout, sys.stderr = orig_out_err


# TODO: --no-cache, --clear-cache, --print0
def main():
  logging.basicConfig(level=logging.INFO)

  prog = os.path.basename(sys.argv[0])
  parser = argparse.ArgumentParser(
    description=(
      'Finds duplicate audio files from two sets of paths by comparing acoustid fingerprints.\n'
      'Each found duplicate is printed in JSON (one per line) in the following format:\n'
      '{"a": "/path/to/a", "b": "/path/to/b", "similarity": 95.23}'
    ),
    epilog=(
      'examples:\n'
      f'  {prog} MUSIC\n'
      '    Find duplicates by comparing the files in MUSIC to themselves\n'
      '\n'
      f'  {prog} MUSIC1 MUSIC2\n'
      '    Find duplicates by comparing the files in MUSIC1 to the files in MUSIC2\n'
      '\n'
      f'  {prog} --a MUSIC1 MUSIC2 --b MUSIC3\n'
      '    Find duplicates by comparing the files in MUSIC1 and MUSIC2 to the files in MUSIC3\n'
      '    (Note that files specified in --a are not compared with other files specified in --a)\n'
    ),
    formatter_class=argparse.RawTextHelpFormatter
  )
  parser.add_argument(
    '--threshold',
    default=0.9,
    type=float,
    help='Print audio files if they are at least THRESHOLD percent similar'
  )
  parser.add_argument(
    '--max-offset',
    default=80,
    type=int,
    help=(
      'The maximum fingerprint offset allowed, higher values allow for a match to be found when the audio is shifted more.\n'
      'The offset is specified in fingerprint frames, which are approximately 1/8th of a second each.'
    )
  )
  parser.add_argument(
    '--sample-time',
    default=90,
    type=int,
    help='The number of seconds of audio to use when generating fingerprints'
  )

  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument(
    '--a',
    action='extend',
    nargs='+',
    metavar='PATHS_A',
    dest='list_a',
    default=[]
  )
  group.add_argument(
    'A',
    nargs='?',
    metavar='PATH_A'
  )

  group = parser.add_mutually_exclusive_group()
  group.add_argument(
    '--b',
    action='extend',
    nargs='+',
    metavar='PATHS_B',
    dest='list_b',
    default=[]
  )
  group.add_argument(
    'B',
    nargs='?',
    metavar='PATH_B'
  )

  args = parser.parse_args()

  paths_a = args.list_a
  if args.A:
    paths_a.append(args.A)
  paths_b = args.list_b
  if args.B:
    paths_b.append(args.B)

  with _std_out_err_redirect_tqdm() as orig_stdout:
    iterator = compare_paths(
      paths_a=paths_a,
      paths_b=paths_b,
      threshold=args.threshold,
      max_offset=args.max_offset,
      sample_time=args.sample_time,
      stdout=orig_stdout
    )

    for res in iterator:
      res.a = str(res.a)
      res.b = str(res.b)
      print(json.dumps(dataclasses.asdict(res)))
