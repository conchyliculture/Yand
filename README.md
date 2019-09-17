# YAND (Yet another NAND dumper)

**WARNING, WRITING HASN'T BEEN TESTED YET**

The script lets you read a whole NAND flash (user data & OOB) to a file, and restore a complete dump on a NAND Flash.

It uses ft2232H to connect to a TSOP48. For the pinout & connections, refer to [this diagram](https://github.com/ohjeongwook/DumpFlash/blob/master/schematics.png).

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

For a first detection of you NAND Flash, run the script with no option. This will attempt autodetection of the flash geometry with ONFI:
```
$ yand_cli.py
Chip model & Manufacturer: MT29F32G08CBACAWP (MICRON)
Page Size : 4320 (4096 + 224)
Blocks number : 4096
Device Size: 4GiB
```

then you can start dumping
```
$ yand_cli.py -r -f dump.bin
<wait>
```

If the flash doesn't support ONFI, you'll have to find the geometry yourself. Use the chip serial number as well as the ID returned but the chip:
```
yand.errors.YandException: Warning: Could not read ONFI info. Please provide geometry
Flash returned "98d384a5"
```

Refer to the device datasheet to do the proper calculations, then set the parameters:
```
yand_cli.py  -P 2048,64 -B 64 -K 65536
Chip model & Manufacturer: Unknown Model (Unknown Manufacturer)
Page Size : 2112 (2048 + 64)
Blocks number : 65536
Device Size: 8GiB
```

If this looks correct to you, start dumping:
```
yand_cli.py  -P 2048,64 -B 64 -K 65536 -r -f dump.bin
```
