"""TODO"""
import argparse

from yand import __version__

from yand import device
from yand import errors


class YandCli:
    """TODO"""
    def __init__(self):
        """TODO"""

        self.parser = None

    def ParseArguments(self):
        """TODO"""
        self.parser = argparse.ArgumentParser()

        self.parser.add_argument('-r', '--read', action='store_true', help='read NAND')
        self.parser.add_argument('-w', '--write', action='store_true', help='write NAND')
        self.parser.add_argument(
            '-f', '--file', action='store', help='file to write to, or read from')

        args = self.parser.parse_args()
        return args

    def Main(self):
        """TODO"""
        options = self.ParseArguments()

        ftdi_nand = device.NAND()
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
