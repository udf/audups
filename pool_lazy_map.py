# orderless and lazy Executor.map, that yields completed futures
import concurrent.futures
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor


def _process_chunk(fn, chunk):
  return [fn(*args) for args in chunk]


def lazy_map(pool: ProcessPoolExecutor, fn, *iterables, chunksize=512):
  jobs = set()
  exhausted = False

  while 1:
    # add more jobs if possible
    while not exhausted and len(jobs) < pool._max_workers * 2:
      chunk = [v for _, v in zip(range(chunksize), zip(*iterables))]
      if not chunk:
        exhausted = True
        break
      jobs.add(pool.submit(_process_chunk, fn, chunk))

    if not jobs:
      break

    # wait on jobs, yielding completed
    done, jobs = concurrent.futures.wait(jobs, timeout=1, return_when=FIRST_COMPLETED)
    for fut in done:
      yield fut