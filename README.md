# YAND (Yet another NAND dumper)

This was heavily inspired from [https://github.com/ohjeongwook/DumpFlash](https://github.com/ohjeongwook/DumpFlash).

YAND aims at making it easy to copy all data from a NAND flash into a file, or the other way around.

The Hardware used is the same as that project. More information regarding the Nand dumping process at:
[https://www.blackhat.com/docs/us-14/materials/us-14-Oh-Reverse-Engineering-Flash-Memory-For-Fun-And-Benefit-WP.pdf](https://www.blackhat.com/docs/us-14/materials/us-14-Oh-Reverse-Engineering-Flash-Memory-For-Fun-And-Benefit-WP.pdf)

## Installation

```
VENV="$(mktemp -d)"
virtualenv -p python3.7 "${VENV}"
source "${VENV}/bin/activate"

git clone https://github.com/conchyliculture/yand
cd yand
python setup.py install
```

## Usage

```
usage: yand_cli.py [-h] [-r] [-w] [-f FILE]

optional arguments:
  -h, --help            show this help message and exit
  -r, --read            read NAND
  -w, --write           write NAND
  -f FILE, --file FILE  file to write to, or read from

```
