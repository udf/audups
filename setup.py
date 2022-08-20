from setuptools import Extension, find_packages, setup


if __name__ == '__main__':
  with open('README.md', 'r') as f:
    long_description = f.read()

  setup(
    name='audups',
    description='Command line tool for finding similar audio files using their AcoustID fingerprints',
    long_description=long_description,
    long_description_content_type='text/markdown',

    url='https://github.com/udf/audups',

    author='Samara',
    author_email='tabhooked@gmail.com',

    license='MIT',

    python_requires='>=3.9',

    classifiers=[
      'Development Status :: 3 - Alpha',

      'Intended Audience :: Developers',
      'Operating System :: POSIX :: Linux',
      'Topic :: Multimedia :: Sound/Audio :: Analysis',

      'License :: OSI Approved :: MIT License',

      'Programming Language :: Python :: 3',
      'Programming Language :: Python :: 3.9',
      'Programming Language :: Python :: 3.10',
    ],

    packages=find_packages(),
    entry_points={
      'console_scripts': ['audups = audups:main']
    },
    ext_modules=[
      Extension(
        'audups.correlate',
        sources = ['audups/correlate.c'],
        extra_compile_args = ['-march=native', '-mtune=native']
      )
    ],
    install_requires=[
      'pyacoustid',
      'audioread',
      'tqdm'
    ]
  )
