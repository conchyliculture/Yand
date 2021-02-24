"""CLI tool for yand module"""
import argparse
import logging
import os
import sys

from yand import __version__

from yand import nand_interface
from yand import errors

def Confirm(message, yes=False):
    """Asks the user for a confirmation.

    Args:
        message(str): the message to display.
        yes(bool): always return True.

    Returns:
        bool: whether the user confirms.
    """
    if yes:
        return True

    answer = None
    while answer not in ['y', 'n', '']:
        answer = input('{0:s} [y/N]'.format(message)).lower()
    return answer == 'y'


def Die(message='Aborting', error_code=1):
    """Prints a message and quits."""
    print(message)
    sys.exit(error_code)


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
        self.parser.add_argument('-V', '--version', action='store_true', help='show version')
        self.parser.add_argument(
            '-y', '--yes', action='store_true', help='don\'t ask for conformation')

        self.parser.add_argument(
            '-l', '--logfile', action='store', default='yand.log',
            help='log debug information to the specified file')
        self.parser.add_argument(
            '-C', '--write_check', action='store_true',
            help='read page after each page write operation')
        self.parser.add_argument(
            '-f', '--file', action='store',
            help='file to write to, or read from. "-" means stdin/stdout')

        functional_group = self.parser.add_argument_group(
            'Function Options', 'Specify what operation to run.')
        functional_group.add_argument(
            '-r', '--read', action='store_true', help='read all NAND Flash')
        functional_group.add_argument(
            '-w', '--write', action='store_true', help='write NAND from a raw dump')
        functional_group.add_argument(
            '-e', '--erase', action='store_true', help='erase blocks')
        functional_group.add_argument(
            '--write_value', action='store', help='fill the NAND with this value.', type=int)
        functional_group.add_argument(
            '--write_pgm', action='store_true',
            help='use a .pgm source image file. Will write the image over and over until the end.')
        functional_group.add_argument(
            '--start', action='store', type=int, default=0,
            help=('Set a start bound for the operation. This bound is included:  range(start, end)'
                  '(for a read or write operation, the unit is a page, for Erase, it is a block'))
        functional_group.add_argument(
            '--end', action='store', type=int, default=None,
            help=('Set a end number for the operation. This bound is excluded: range(start, end)'
                  '(for a read or write operation, the unit is a page, for Erase, it is a block'))

        geometry_group = self.parser.add_argument_group(
            'Geometry options',
            'Specify the geometry of the NAND flash if it can\'t be detected via ONFI.')
        geometry_group.add_argument(
            '-P', '--page_size', action='store',
            help='specify page size and OOB size in bytes, with the format: "2048,128"')
        geometry_group.add_argument(
            '-B', '--pages_per_block', action='store', help='number of pages per block')
        geometry_group.add_argument(
            '-K', '--number_of_blocks', action='store', help='total number of blocks')


        args = self.parser.parse_args()
        return args

    def Main(self):
        """Main function"""

        options = self.ParseArguments()

        if options.version:
            print('{0:s}: {1:s}'.format(__file__, __version__))
            sys.exit(0)

        if options.logfile:
            logging.basicConfig(
                filename=options.logfile,
                level=logging.DEBUG,
                format='%(asctime)s %(message)s',
                datefmt='[%Y-%m-%d %H:%M:%S]'
            )

        ftdi_nand = nand_interface.NandInterface()

        if not ftdi_nand:
            self.parser.print_help()
            raise errors.YandException('Need a source to read from')

        # Set up geometry
        if options.page_size:
            try:
                page_size, oob_size = [
                    int(opt) for opt in options.page_size.split(',')]
                ftdi_nand.oob_size = oob_size
                ftdi_nand.page_size = oob_size + page_size
            except ValueError as value_error:
                raise errors.YandException(
                    'Please specify page size as such : "user_data,oob". For example: "2048,128"'
                    ) from value_error
        if options.pages_per_block:
            ftdi_nand.pages_per_block = int(options.pages_per_block)
        if options.number_of_blocks:
            ftdi_nand.number_of_blocks = int(options.number_of_blocks)

        ftdi_nand.Setup()
        infos = 'Chip info: '+ftdi_nand.GetInfos()
        logging.debug(infos)

        if not options.file == '-':
            print(infos)

        if options.read:
            if not options.file:
                Die('Need a destination file (hint: -f)')
            if os.path.exists(options.file):
                if not Confirm(
                        'Destination file {0:s} already exists. Proceed?'.format(options.file),
                        options.yes):
                    Die()
            logging.debug(
                'Starting a read operation (start={0:d}, end={1:d}, destination={2:s})'.format(
                    options.start, options.end or -1, options.file))

            ftdi_nand.DumpFlashToFile(options.file, start_page=options.start, end_page=options.end)
        elif options.write:
            if not Confirm(
                    'Reminder: '
                    'You need to erase the entire flash with -e for this to work as expected\n\n'
                    'About to write the content of "{0:s}" to NAND Flash. Proceed?'.format(
                        options.file), options.yes):
                Die()
            logging.debug(
                'Starting an Dump write operation with file {0:s} (write check is {1!s})'.format(
                    options.file, options.write_check))
            ftdi_nand.WriteFileToFlash(options.file, write_check=options.write_check)
        elif options.erase:
            if not Confirm('About to erase NAND Flash blocks. Proceed?', options.yes):
                Die()
            logging.debug(
                'Starting an erase operation (start={0:d}, end={1:d})'.format(
                    options.start, options.end or -1))
            ftdi_nand.Erase(start_block=options.start, end_block=options.end)
        elif options.write_value is not None:
            if not Confirm(
                    'About to write value {0:d} in NAND Flash. Proceed?'.format(
                        options.write_value), options.yes):
                Die()
            logging.debug(
                'Starting a fill value operation '
                '(start={0:d}, end={1:d}, value={2:d}, write check is {3!s})'.format(
                    options.start, options.end or -1, options.write_value, options.write_check))
            ftdi_nand.FillWithValue(
                options.write_value, start_page=options.start, end_page=options.end,
                write_check=options.write_check)
        elif options.write_pgm:
            if not Confirm(
                    'About to write content of {0:s} in NAND Flash. Proceed?'.format(
                        options.file), options.yes):
                sys.exit(1)
            logging.debug(
                'Starting a write pgm operation '
                '(start={0:d}, end={1:d}, pgm_file={2:s}, write check is {3!s})'.format(
                    options.start, options.end or -1, options.file, options.write_check))
            ftdi_nand.WritePGMToFlash(
                options.file, start_page=options.start, end_page=options.end,
                write_check=options.write_check)


if __name__ == "__main__":
    C = YandCli()
    C.Main()
