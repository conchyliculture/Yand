# YAND (Yet another NAND dumper)

No-bullshit NAND Flash dumper / reader using PyFTDI to harness glorious FT2232H BitBanging

Mandatory warning: *I am NOT responsible to any damage done to your data and/or devices*

## What YAND is

YAND aims at making it easy to copy all data from a NAND flash into a file, or the other way around.

It uses FT2232H chip enabled board to connect to a TSOP48, via a serial over USB conenction.
For the pinout & schematics, refer to [this diagram](https://github.com/ohjeongwook/DumpFlash/blob/master/schematics.png).

This was heavily inspired from [https://github.com/ohjeongwook/DumpFlash](https://github.com/ohjeongwook/DumpFlash).

The Hardware used is the same as that project. More information regarding the Nand dumping process at:
[https://www.blackhat.com/docs/us-14/materials/us-14-Oh-Reverse-Engineering-Flash-Memory-For-Fun-And-Benefit-WP.pdf](https://www.blackhat.com/docs/us-14/materials/us-14-Oh-Reverse-Engineering-Flash-Memory-For-Fun-And-Benefit-WP.pdf)

## What YAND is NOT

It is *NOT* going to do your homework trying to figure out NAND flash geometry.

While it supports [ONFI](http://www.onfi.org/) autodetection, if this isn't offered by your chip, you're on your own to hunt for these delicious datasheet.

It is NOT going to be smart in anyway, trying to avoid bad blocks or calculate ECC for you. That is your problem.

It is also NOT fast... Expected speeds are ~100kbps for reading & writing pages. Expect a couple hours to dump a whole 1GiB chip.

## Installation

Make yourself a nice and cozy Python3.7 environment.

```
VENV="$(mktemp -d)"
virtualenv -p python3.7 "${VENV}"
source "${VENV}/bin/activate"

git clone https://github.com/conchyliculture/yand
cd yand
python setup.py install
```

## Usage


First, make sure your NAND Flash is detected properly, run the script with no option. This will attempt autodetection of the flash geometry with ONFI:
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

Refer to the device datasheet to do the proper calculations, then set the required parameters: page size, number of page per block, total number of blocks.
Make sure the calculated device size is correct.
```
yand_cli.py  -P 2048,64 -B 128 -K 4096
Chip model & Manufacturer: Unknown Model (Unknown Manufacturer)
Page Size : 2112 (2048 + 64)
Blocks number : 65536
Device Size: 8GiB
```

If this looks correct to you, start dumping:

```
alias yand='yand_cli.py  -P 2048,64 -B 128 -K 4096' # Helps not having to re-type geometry options every operation
yand -r -f dump.bin
```

## Options

```
usage: yand_cli.py [-h] [-V] [-l LOGFILE] [-C] [-f FILE] [-r] [-w] [-e]
                   [--write_value WRITE_VALUE] [--write_pgm] [--start START]
                   [--end END] [-P PAGE_SIZE] [-B PAGES_PER_BLOCK]
                   [-K NUMBER_OF_BLOCKS]

optional arguments:
  -h, --help            show this help message and exit
  -V, --version         show version
  -l LOGFILE, --logfile LOGFILE
                        log debug information to the specified file
  -C, --write_check     read page after each page write operation
  -f FILE, --file FILE  file to write to, or read from. "-" means stdin/stdout

Function Options:
  Specify what operation to run.

  -r, --read            read all NAND Flash
  -w, --write           write NAND from a raw dump
  -e, --erase           erase blocks
  --write_value WRITE_VALUE
                        fill the NAND with this value.
  --write_pgm           use a .pgm source image file. Will write the image
                        over and over until the end.
  --start START         Set a start bound for the operation. This bound is
                        included: range(start, end)(for a read or write
                        operation, the unit is a page, for Erase, it is a
                        block
  --end END             Set a end number for the operation. This bound is
                        excluded: range(start, end)(for a read or write
                        operation, the unit is a page, for Erase, it is a
                        block

Geometry options:
  Specify the geometry of the NAND flash if it can't be detected via ONFI.

  -P PAGE_SIZE, --page_size PAGE_SIZE
                        specify page size and OOB size in bytes, with the
                        format: "2048,128"
  -B PAGES_PER_BLOCK, --pages_per_block PAGES_PER_BLOCK
                        number of pages per block
  -K NUMBER_OF_BLOCKS, --number_of_blocks NUMBER_OF_BLOCKS
                        total number of blocks
```

## Visualization

Do you want to look into your NAND dump?

![Demo](doc/giphy.gif)

Go read the relevant [doc](TOOLS.md) to see your dump in a fancy JS zoom thing.
