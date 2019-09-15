"""TODO"""
import argparse

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
        self.parser.add_argument(
            '-s', '--source', choices=['ftdi'], action='store', help='where to read from')
        self.parser.add_argument(
            '-o', '--output', action='store', help='Destination file')

        args = self.parser.parse_args()
        return args

    def Main(self):
        """TODO"""
        options = self.ParseArguments()

        source = None

        if options.source == 'ftdi':
            source = device.NAND()
            source.Setup()
            print(source.GetInfos())

        if options.read:
            if not source:
                self.parser.print_help()
                raise errors.YandException('Need a source to read from')
            source.Dump(destination=options.output)



if __name__ == "__main__":
    cli = YandCli()
    cli.Main()
