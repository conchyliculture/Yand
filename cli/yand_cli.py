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

        self.parser.add_argument(
            '-P', '--pagesize', action='store',
            help='Specify page size  & OOB size in bytes, ie: "2048,128"')
        self.parser.add_argument(
            '-B', '--pages_per_block', action='store', help='Specify the number of pages per block')
        self.parser.add_argument(
            '-K', '--number_of_blocks', action='store', help='Specify the number blocks')

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


        if options.pagesize:
            try:
                ftdi_nand.page_size, ftdi_nand.oob_size = [
                    int(opt) for opt in options.pagesize.split(',')]
            except ValueError:
                raise errors.YandException(
                    'Please specify page size as such : "user_data,oob". For example: "2048,128"')
        if options.pages_per_block:
            ftdi_nand.pages_per_block = int(options.pages_per_block)
        if options.number_of_blocks:
            ftdi_nand.number_of_blocks = int(options.number_of_blocks)

        ftdi_nand.Setup()


        print(ftdi_nand.GetInfos())

        if options.read:
            ftdi_nand.DumpFlashToFile(options.file)
        elif options.write:
            ftdi_nand.WriteFileToFlash(options.file)


if __name__ == "__main__":
    cli = YandCli()
    cli.Main()
