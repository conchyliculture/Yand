"""CLI tool for yand module"""
import argparse
import sys

from yand import __version__

from yand import nand_interface
from yand import errors


class YandCli:
    """TODO"""
    def __init__(self):
        """TODO"""

        self.parser = None

    def ParseArguments(self):
        """TODO"""
        self.parser = argparse.ArgumentParser()

        self.parser.add_argument('-V', '--version', action='store_true', help='Show version')
        self.parser.add_argument('-r', '--read', action='store_true', help='Read all NAND Flash')
        self.parser.add_argument(
            '-w', '--write', action='store_true', help='Write NAND from a raw dump')
        self.parser.add_argument(
            '-f', '--file', action='store', help='File to write to, or read from')

        args = self.parser.parse_args()
        return args

    def Main(self):
        """Main function"""
        options = self.ParseArguments()
        if options.version:
            print('{0:s}: {1:s}'.format(__file__, __version__))
            sys.exit(0)

        ftdi_nand = nand_interface.NandInterface()

        if not ftdi_nand:
            self.parser.print_help()
            raise errors.YandException('Need a source to read from')

        ftdi_nand.Setup()
        print(ftdi_nand.GetInfos())

        if options.read:
            ftdi_nand.DumpFlashToFile(options.file)
        elif options.write:
            ftdi_nand.WriteFileToFlash(options.file)


if __name__ == "__main__":
    cli = YandCli()
    cli.Main()
