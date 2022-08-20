import logging
import sys
import contextlib

import tqdm
from tqdm.contrib.logging import tqdm_logging_redirect


logger = logging.getLogger('audups')


@contextlib.contextmanager
def dynamic_tqdm(*tqdm_args, **tqdm_kwargs):
  """Context manager that returns a tqdm object or None depending on context."""
  with contextlib.ExitStack() as cm:
    if sys.stderr.isatty() and logger.isEnabledFor(logging.INFO):
      progress = cm.enter_context(tqdm_logging_redirect(
        *tqdm_args,
        loggers=[logger],
        **tqdm_kwargs
      ))
    else:
      progress = None
    yield progress
