import logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('audedup')

# TODO: convert to parameters
# seconds to sample audio file for
sample_time = 90
# number of workers
n_workers = 32
# return info if files are >= this similarity %
threshold = 0.8