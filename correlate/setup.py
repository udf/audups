from setuptools import setup, Extension

setup(
  name='correlate',
  ext_modules = [
    Extension(
      'correlate',
      sources = ['correlate.c'],
      extra_compile_args = ["-march=native", "-mtune=native"]
    )
  ]
)