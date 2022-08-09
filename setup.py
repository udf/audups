from setuptools import setup, Extension

VERSION = '0.1'

if __name__ == '__main__':
  setup(
    name='audups',
    version=VERSION,
    python_requires='>=3.9',
    scripts=['audups.py'],
    ext_modules=[
      Extension(
        'audups.correlate',
        sources = ['audups/correlate.c'],
        extra_compile_args = ["-march=native", "-mtune=native"]
      )
    ],
    install_requires=[
      'pyacoustid',
      'audioread'
    ]
  )