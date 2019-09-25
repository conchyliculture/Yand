"""Helper methods."""

from io import BytesIO
from io import SEEK_CUR
from io import SEEK_SET
import logging

from yand import errors

def Diff(a, b):
    """Returns the number of different elements between 2 interables.

    Args:
        a(iterable): first iterable.
        b(iterable): second iterable.
    Returns:
        int: the number of different elements.
    """
    return sum(map(lambda x, y: bool(x-y), a, b))

class RingBytesIO(BytesIO):
    """Implements a 'ring' BytesIO, that starts from the beggining of the buffer when
    the end is reached."""

    def seek(self, offset, whence):
        super().seek(offset % len(self.getvalue()), whence)

    def read(self, l):
        res = b''
        while len(res) < l:
            bytes_left = l - len(res)
            r = super().read(bytes_left)
            res += r
            if len(r) < bytes_left:
                self.seek(0, SEEK_SET)
                res += super().read(l - len(res))
        return res

class PGMReader:
    """Context manager to get information about a PGM file."""

    def __init__(self, pgm_filepath):
        """Initializs a PGMReader class.

        Args:
            pgm_filepath(str): the path to the file.
        """
        self.filepath = pgm_filepath
        self.file = open(pgm_filepath, 'rb')

        self.width = 0
        self.height = 0
        self.header_length = 0

        self._ParseHeader()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.file.close()

    def _ParseHeader(self):
        self.header_length = 0
        magic = self.file.read(3)
        if magic != b'P5\x0a':
            raise errors.YandException(
                'Input file {0:s} is not a PGM picture (bad magic \'{1!s}\')'.format(
                    self.filepath, magic))
        self.header_length += 3
        comment = b''
        bb = self.file.read(1)
        self.header_length += 1
        while bb != b'\x0a':
            # Comment
            comment += bb
            bb = self.file.read(1)
            self.header_length += 1
        while self.file.read(1) == b'\x0a':
            self.header_length += 1
        self.file.seek(-1, SEEK_CUR)
        dimensions = b''
        bb = self.file.read(1)
        while bb != b'\x0a':
            dimensions += bb
            bb = self.file.read(1)
        self.header_length += len(dimensions) + 1
        self.width, self.height = [int(d) for d in dimensions.split(b' ')]
        if self.file.read(4) != b'255\x0a':
            raise errors.YandException((
                'Input file {0:s} is not a PGM picture '
                '(should have 255 as max value)').format(self.filepath))
        self.header_length += 4

    def Read(self, x, y, length):
        """Returns data from the pgm file.

        Args:
            x(int): the position in width starting from top.
            y(int): position in height starting from top.
            length(int): the amount of data to read
        Returns:
            bytearray: the data read from the picture, padded with 0xFF
        """
        # Skip header
        self.file.seek(self.header_length, SEEK_SET)
        if y > self.height:
            logging.debug((
                'warning, reading more ({0:d}) than input picture height ({1:d})'
                'returning 0xFFs'
                ).format(y, self.height))
            return bytearray([0xff]*length)
        if x > self.width:
            logging.debug((
                'warning, reading more ({0:d}) than input picture width ({1:d})'
                'returning 0xFFs'
                ).format(x, self.height))
            return bytearray([0xff]*length)

        self.file.seek(y * self.width + x, SEEK_CUR) # We want to skip header

        amount_to_read = length
        if x + length > self.width:
            amount_to_read = self.width

        data = self.file.read(amount_to_read)
        return bytearray(data.ljust(length, b'\xff'))
