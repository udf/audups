# audups
Command line tool for finding similar audio files using their [AcoustID fingerprints](https://acoustid.org/)

## Requirements
- [chromaprint](https://acoustid.org/chromaprint) (for fingerprint calculation)
- [ffmpeg](https://ffmpeg.org/) (to read audio files)

Note that this project is only intended to be used on Linux, support for other operating systems will not be provided.

## Usage
`audups /path/to/music`  
  Compare the files in `/path/to/music` with themselves, printing similar ones.  
  You can set the threshold at which matches are printed using `--threshold x`, where `x` is a number between 0.0 and 1.0.

`audups MUSIC1 MUSIC2`  
  Compares the files in `MUSIC1` to the files in `MUSIC2`

`audups --a MUSIC1 MUSIC2 --b MUSIC3`  
  Compares the files in `MUSIC1` and `MUSIC2` to the files in `MUSIC3`  
  (Note that files specified in --a are not compared with other files specified in --a)
