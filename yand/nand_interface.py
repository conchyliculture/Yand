"""Module to talk to a NAND"""

from io import BytesIO
from io import SEEK_CUR, SEEK_SET
import logging
import os
import sys
from tqdm import tqdm

from yand import errors
from yand import ftdi_device

logging.basicConfig(filename='/tmp/yand.log', level=logging.INFO)


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

class NandInterface:
    """Class to operate on a NAND Flash"""

    NAND_CMD_READ0 = 0x00
    NAND_CMD_PROG_PAGE_START = 0x10
    NAND_CMD_READSTART = 0x30
    NAND_CMD_ERASE = 0x60
    NAND_CMD_STATUS = 0x70
    NAND_CMD_PROG_PAGE = 0x80
    NAND_CMD_READID = 0x90
    NAND_CMD_READ_PARAM_PAGE = 0xEC
    NAND_CMD_ERASE_START = 0xD0

    NAND_ADDR_ID = 0x00
    NAND_ADDR_ONFI = 0x20

    NAND_SIZE_ONFI = 0x100

    def __init__(self):
        """Initializes a NandInterface object"""
        self.ftdi_device = None

        # Flash geometry / config
        self.address_cycles = 5
        self.device_manufacturer = 'Unknown Manufacturer'
        self.device_model = 'Unknown Model'
        self.manufacturer_id = None
        self.number_of_blocks = None
        self.oob_size = None
        self.page_size = None
        self.pages_per_block = None

    def GetTotalSize(self):
        """Returns the total size of the flash, in bytes"""
        return self.page_size * self.GetTotalPages()

    def GetTotalPages(self):
        """Returns the number of pages of the Flash."""
        return self.number_of_blocks * self.pages_per_block

    def GetInfos(self):
        """Returns a string showing Flash info"""
        size = self.GetTotalSize()
        if size > 1024*1024*1024:
            size = '{0:d}GiB'.format(int(size / (1024*1024*1024)))
        elif size > 1024*1024:
            size = '{0:d}MiB'.format(int(size / (1024*1024)))
        return """Chip model & Manufacturer: {0:s} ({1:s})
Page Size : {2:d} ({3:d} + {4:d})
Blocks number : {5:d}
Device Size: {6:s}
        """.format(
            self.device_model.strip(), self.device_manufacturer.strip(),
            self.page_size, (self.page_size - self.oob_size), self.oob_size,
            self.number_of_blocks, size
        )

    def _SetupFlash(self):
        """Setup the flash configuration."""

        # First we check if we can gather information form ONFI
        self.SendCommand(self.NAND_CMD_READID)
        self.SendAddress(self.NAND_ADDR_ONFI)
        onfi_result = self.ftdi_device.Read(4)

        if onfi_result == b'ONFI':
            self.SendCommand(self.NAND_CMD_READ_PARAM_PAGE)
            self.SendAddress(self.NAND_ADDR_ID)
            self.ftdi_device.WaitReady()
            onfi_data = self.ftdi_device.Read(self.NAND_SIZE_ONFI)
            self._ParseONFIData(onfi_data)
        else:
            raise errors.YandException(
                'Warning: Could not read ONFI info. Please provide geometry\n'
                'Flash returned "{0:s}"'.format(onfi_result.hex()))

    def _ParseONFIData(self, onfi_data):
        """Parses a ONFI data block."""
        # Check ONFI magic
        if onfi_data[0:4] != bytearray([0x4F, 0x4E, 0x46, 0x49]):
            raise errors.YandException('ONFI data block does not start with \'ONFI\'')

        # Parses ONFI version support
        _ = onfi_data[4:6]
        # Parses features support
        _ = onfi_data[6:8]
        # Parses optional commands support
        _ = onfi_data[8:10]

        # extended page parameter length
        _ = onfi_data[12:14]
        # Number of parameter pages
        _ = onfi_data[14]

        self.device_manufacturer = onfi_data[32:44].decode()
        self.device_model = onfi_data[44:64].decode()

        # 1 byte manufacturer ID
        self.manufacturer_id = onfi_data[64]

        # 'user data' bytes per page
        user_size = int.from_bytes(onfi_data[80:84], byteorder='little')
        # spare/OOB size per page
        self.oob_size = int.from_bytes(onfi_data[84:86], byteorder='little')
        self.page_size = user_size + self.oob_size

        self.pages_per_block = int.from_bytes(onfi_data[92:96], byteorder='little')

        # Number of blocks per LUN
        number_blocks_per_lun = int.from_bytes(onfi_data[96:100], byteorder='little')

        # Number of LUNs per chip enable
        number_lun_per_chip = onfi_data[100]
        self.number_of_blocks = number_blocks_per_lun * number_lun_per_chip

        address_cycles = onfi_data[101]
        self.address_cycles = (address_cycles & 0x0f) + ((address_cycles & 0xf0) >> 4)

    def Setup(self):
        """Sets the underlying IO and flash characteristics"""
        if not self.ftdi_device:
            self.ftdi_device = ftdi_device.FtdiDevice()
            self.ftdi_device.Setup()

        if not (self.page_size and self.pages_per_block and self.number_of_blocks):
            self._SetupFlash()

    def DumpFlashToFile(self, destination, start_page=0, end_page=None):
        """Reads all pages from the flash, and writes it to a file.

        Args:
            destination(str): the destination file.
            start_page(int): Page to start dumping from.
            end_page(int): Page to stop dumping at. Default is to the end.
        Raises:
            errors.YandException: if no destination file is provided.
        """
        if not destination:
            raise errors.YandException('Please specify where to write')

        if not end_page:
            end_page = self.GetTotalPages()

        if destination == "-":
            for page in range(start_page, end_page):
                sys.stdout.buffer.write(self.ReadPage(page))
        else:
            progress_bar = tqdm(
                total=self.GetTotalPages() * self.page_size,
                unit_scale=True,
                unit_divisor=1024,
                unit='B'
            )
            with open(destination, 'wb') as dest_file:
                for page in range(start_page, end_page):
                    dest_file.write(self.ReadPage(page))
                    progress_bar.update(self.page_size)

    def SendCommand(self, command):
        """Sends a command address to the Flash.

        Args:
            command(int): the command to send.
        """
        self.ftdi_device.Write(bytearray([command]), command=True)


    def ReadPage(self, page_number):
        """Returns the content of a page.

        Args:
            page_number(int): the page to read.
        Returns:
            bytearray: the content of the page.
        """
        page_address = page_number << 16
        self.SendCommand(self.NAND_CMD_READ0)
        self.SendAddress(page_address, self.address_cycles)
        self.SendCommand(self.NAND_CMD_READSTART)
        bytes_to_read = self.ftdi_device.Read(self.page_size)
        return bytes_to_read

    def SendAddress(self, address, size=1):
        """Writes an address to the NAND Flash.

        Args:
            address(int): the address to set.
            size(int): the number LSB to send (ie: "address cycles").
        """
        data = (address).to_bytes(8, byteorder='little')
        self.ftdi_device.Write(data[0:size], address=True)

    def EraseBlock(self, block):
        """Erase a block

        Args:
            block(int): the block to erase.
        """
        row = block * self.pages_per_block
        self.ftdi_device.write_protect = False
        self.SendCommand(self.NAND_CMD_ERASE)
        self.SendAddress(row, self.address_cycles) # Is 3 always the case?
        self.SendCommand(self.NAND_CMD_ERASE_START)
        self.ftdi_device.WaitReady()
        self.ftdi_device.write_protect = True
        logging.debug('erased block {0:d}'.format(block))

    def WritePage(self, page_number, data):
        """Writes a page to the NAND Flash

        Args:
            page_number(int): the number of the page.
            data(bytearray): the data to program.
        Raises:
            errors.YandException: if trying to write more data than a block length.
        """
        if not len(data) == self.page_size:
            raise errors.YandException(
                'Trying to write data that is different than page_size: {0:d} != {1:d}'.format(
                    len(data), self.page_size))
        self.ftdi_device.write_protect = False

        page_address = page_number << 16

        self.SendCommand(self.NAND_CMD_PROG_PAGE)
        self.ftdi_device.WaitReady()
        self.SendAddress(page_address, self.address_cycles)
        self.ftdi_device.WaitReady()
        self.ftdi_device.Write(data)
        self.SendCommand(self.NAND_CMD_PROG_PAGE_START)
        self.ftdi_device.WaitReady()
        self.CheckStatus()
        logging.debug('written page {0:d} (addr: {1:d})'.format(page_number, page_address))

        self.ftdi_device.write_protect = True

    def CheckStatus(self):
        """Check the status of the last operation."""
        self.SendCommand(self.NAND_CMD_STATUS)
        status = self.ftdi_device.Read(1)[0]
        if (status & 0x2) == 0x2 and (status & 0x20 == 0x20):
            # applies to PROGRAM-, and COPYBACK PROGRAM-series operations
            raise errors.StatusProgramError('Status is {0:s}'.format(status.hex()))
        if (status & 0x1) == 0x1 and (status & 0x10 == 0x10):
            # applies to PROGRAM-, ERASE-, and COPYBACK PROGRAM-series operations
            raise errors.StatusProgramError('Status is {0:s}'.format(status.hex()))

    def Erase(self, start_block=0, end_block=None):
        """Erase all blocks in the NAND Flash.

        Args:
            start_block(int): erase from this block number.
            end_block(int): erase up to this block. Default is to the end."""

        if not end_block:
            end_block = self.number_of_blocks

        progress_bar = tqdm(
            total=(end_block - start_block) * (self.pages_per_block * self.page_size),
            unit_scale=True,
            unit_divisor=1024,
            unit='B'
        )
        for block in range(start_block, end_block):
            self.EraseBlock(block)
            progress_bar.update(self.page_size * self.pages_per_block)

    def FillWithValue(self, value, start=0, end=None):
        """Fill NAND flash pages with a specific value.

        Args:
            value(int): the value to write.
            start(int): the first page to write.
            end(int): write pages until this one (excluded).
        """
        total_size = self.GetTotalSize()

        if end == -1:
            end = int(total_size / self.page_size)
        else:
            total_size = (end - start) * self.page_size

        progress_bar = tqdm(
            total=total_size,
            unit_scale=True,
            unit_divisor=1024,
            unit='B'
        )
        for page_number in range(start, end or self.GetTotalPages()):
            self.WritePage(page_number, bytearray([value]*self.page_size))
            progress_bar.update(self.page_size)


    def WriteFileToFlash(self, filename):
        """Overwrite file to NAND Flash.

        Args:
            filename(str): path to the dump to write.
        Raises:
            errors.YandException: if filename has more data than the NAND Flash.
        """
        filesize = os.stat(filename).st_size
        if filesize > self.GetTotalSize():
            raise errors.YandException(
                'Input file is {0:d} bytes, more than the current NAND Flash size ({1:d})'.format(
                    filesize, self.GetTotalSize()))
        if filesize < self.GetTotalSize():
            print('input file is {0:d}, less than the current NAND Flash size ({1:d})'.format(
                filesize, self.GetTotalSize()))

        progress_bar = tqdm(
            total=self.GetTotalSize(),
            unit_scale=True,
            unit_divisor=1024,
            unit='B'
        )
        with open(filename, 'rb') as input_file:
            for page_number in range(self.GetTotalPages()):
                page_data = input_file.read(self.page_size)
                self.WritePage(page_number, page_data)
                progress_bar.update(self.page_size)

    def ReadPageFromPic(self, pic, picture_width, picture_height, x=0, y=0):
        """Returns data from a pgm file at a specific offset, that's one page length.

        Args:
            pic(file): the opened file like object
            picture_width(int): the width of the input picture
            picture_height(int): the height of the input picture
            x(int): the position in width starting from top.
            y(int): position in height starting from top.
        Returns:
            bytearray: the data read from the picture, padded with 0xFF
        """
        if y > picture_height:
            print((
                'warning, reading more ({0:d}) than input picture height ({1:d})'
                'returning 0xFFs'
                ).format(y, picture_height))
            return bytearray([0xff]*self.page_size)
        if x > picture_width:
            print((
                'warning, reading more ({0:d}) than input picture width ({1:d})'
                'returning 0xFFs'
                ).format(x, picture_height))
            return bytearray([0xff]*self.page_size)

        pic.seek(y*picture_width + x, SEEK_CUR) # We want to skip header

        amount_to_read = self.page_size
        if x + self.page_size > picture_width:
            amount_to_read = picture_width

        data = pic.read(amount_to_read)
        return bytearray(data.ljust(self.page_size, b'\xff'))

    def WritePGMToFlash(self, filename, start_page=0, end_page=None):
        """Writes a picture to the NAND.

        Args:
            filename(str): the path to the file to write.
        Raises:
            errors.YandException: if something goes wrong.
        """
        header_length = 0
        if not end_page:
            end_page = self.GetTotalPages()
        with open(filename, 'rb') as source_pic:
            magic = source_pic.read(3)
            if magic != b'P5\x0a':
                raise errors.YandException(
                    'Input file {0:s} is not a PGM picture (bad magic \'{1!s}\')'.format(
                        filename, magic))
            header_length += 3
            comment = b''
            bb = source_pic.read(1)
            header_length += 1
            while bb != b'\x0a':
                # Comment
                comment += bb
                bb = source_pic.read(1)
                header_length += 1
            while source_pic.read(1) == b'\x0a':
                header_length += 1
            source_pic.seek(-1, SEEK_CUR)
            dimensions = b''
            bb = source_pic.read(1)
            while bb != b'\x0a':
                dimensions += bb
                bb = source_pic.read(1)
            header_length += len(dimensions) + 1
            picture_width, picture_height = [int(d) for d in dimensions.split(b' ')]
            if source_pic.read(4) != b'255\x0a':
                raise errors.YandException((
                    'Input file {0:s} is not a PGM picture '
                    '(should have 255 as max value)').format(filename))
            header_length += 4

            progress_bar = tqdm(
                total=(end_page - start_page) * self.page_size,
                unit_scale=True,
                unit_divisor=1024,
                unit='B'
            )
            x = 0
            y = 0
            for page_number in range(start_page, end_page):
                source_pic.seek(header_length, SEEK_SET)
                data = self.ReadPageFromPic(source_pic, picture_width, picture_height, x, y)
                self.WritePage(page_number, data)
                progress_bar.update(self.page_size)
                y += 1
                if y == picture_height:
                    x += self.page_size
                    y = 0
