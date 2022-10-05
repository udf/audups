import logging
import sys
import contextlib

from tqdm.contrib import DummyTqdmFile
from tqdm.contrib.logging import tqdm_logging_redirect


logger = logging.getLogger('audups')


@contextlib.contextmanager
def dynamic_tqdm(*tqdm_args, **tqdm_kwargs):
  """Context manager that returns a tqdm object or None depending on context."""
  orig_out = sys.stdout
  try:
    # redirect stdout to stderr only in tty
    if orig_out.isatty():
      sys.stdout = DummyTqdmFile(sys.stderr)
    with contextlib.ExitStack() as cm:
      if sys.stderr.isatty() and logger.isEnabledFor(logging.INFO):
        progress = cm.enter_context(tqdm_logging_redirect(
          *tqdm_args,
          **tqdm_kwargs
        ))
      else:
        progress = None
      yield progress
  except Exception as exc:
    raise exc
  finally:
    sys.stdout = orig_out
