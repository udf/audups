# number of points to scan cross correlation over
span = 80
# step size (in points) of cross correlation
step = 1

popcnt_table_8bit = bytes(bin(x).count('1') for x in range(256))

def popcnt(x):
  """
  Count the number of set bits in the given 32-bit integer.
  """
  return (
    popcnt_table_8bit[(x >>  0) & 0xFF] +
    popcnt_table_8bit[(x >>  8) & 0xFF] +
    popcnt_table_8bit[(x >> 16) & 0xFF] +
    popcnt_table_8bit[(x >> 24) & 0xFF]
  )


def cross_correlation(listx, listy, offset):
  if offset > 0:
    listx = listx[offset:]
  elif offset < 0:
    listy = listy[-offset:]

  error = 0
  for x, y in zip(listx, listy):
    error += popcnt(x ^ y)
  return 1.0 - error / 32.0 / min(len(listx), len(listy))


def get_max_corr(listx, listy, span, step):
  best_corr = 0
  best_offset = 0
  for offset in range(-span, span + 1, step):
    corr = cross_correlation(listx, listy, offset)
    if corr > best_corr:
      best_corr = corr
      best_offset = offset
  return best_corr, best_offset


def correlate(source, target):
  return get_max_corr(source, target, span, step)
