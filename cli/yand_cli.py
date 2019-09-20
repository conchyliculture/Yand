"""CLI tool for yand module"""
import argparse
import sys

from yand import __version__

from yand import nand_interface
from yand import errors


class YandCli:
    """Tool to use the Yand module"""
    def __init__(self):
        """Initializes a YandCli object."""
        self.parser = None

    def ParseArguments(self):
        """Parses arguments.

        Returns:
            argparse.NameSpace: the parsed options.
        """
        self.parser = argparse.ArgumentParser()

        self.parser.add_argument('-V', '--version', action='store_true', help='Show version')
        self.parser.add_argument('-r', '--read', action='store_true', help='Read all NAND Flash')
        self.parser.add_argument(
            '-w', '--write', action='store_true', help='Write NAND from a raw dump')
        self.parser.add_argument(
            '-e', '--erase', action='store_true', help='Erase blocks')
        self.parser.add_argument(
            '-f', '--file', action='store',
            help='File to write to, or read from. "-" means stdin/stdout')
        self.parser.add_argument(
            '--write_value', action='store', help='Fill with this value.')

        self.parser.add_argument(
            '-P', '--page_size', action='store',
            help='Specify page size  & OOB size in bytes, ie: "2048,128"')
        self.parser.add_argument(
            '-B', '--pages_per_block', action='store', help='Specify the number of pages per block')
        self.parser.add_argument(
            '-K', '--number_of_blocks', action='store', help='Specify the number blocks')

        self.parser.add_argument(
            '--start', action='store', type=int, default=0,
            help=('Set a start bound for the operation. This bound is included.'
                  '(for a READ operation, te unit is a page, a block for writing/erase'))
        self.parser.add_argument(
            '--end', action='store', type=int, default=-1,
            help=('Set a end number for the operation. This bound is excluded.'
                  '(for a READ operation, te unit is a page, a block for writing/erase'))

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


        if options.page_size:
            try:
                page_size, oob_size = [
                    int(opt) for opt in options.page_size.split(',')]
                ftdi_nand.oob_size = oob_size
                ftdi_nand.page_size = oob_size + page_size
            except ValueError:
                raise errors.YandException(
                    'Please specify page size as such : "user_data,oob". For example: "2048,128"')
        if options.pages_per_block:
            ftdi_nand.pages_per_block = int(options.pages_per_block)
        if options.number_of_blocks:
            ftdi_nand.number_of_blocks = int(options.number_of_blocks)

        ftdi_nand.Setup()

        if not options.file == '-':
            print(ftdi_nand.GetInfos())

        if options.read:
            ftdi_nand.DumpFlashToFile(options.file, start=int(options.start), end=int(options.end))
        elif options.write:
            ftdi_nand.WriteFileToFlash(options.file)
        elif options.erase:
            ftdi_nand.Erase(start=options.start, end=options.end)
        elif options.write_value:
            ftdi_nand.FillWithValue(
                int(options.write_value), start=options.start, end=options.end)


if __name__ == "__main__":
    cli = YandCli()
    cli.Main()
