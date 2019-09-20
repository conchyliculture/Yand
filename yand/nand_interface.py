"""Module to talk to a NAND"""

from io import BytesIO
from io import SEEK_SET
import os
import sys
from tqdm import tqdm

from yand import errors
from yand import ftdi_device

class RingBytesIO(BytesIO):
    """Implements a 'ring' BytesIO, that starts from the beggining of the buffer when
    the end is reached."""

    def seek(self, offset, whence=SEEK_SET):
        super().seek(offset % len(self.getvalue()), whence=whence)

    def read(self, l):
        res = b''
        while len(res) < l:
            bytes_left = l - len(res)
            r = super().read(bytes_left)
            res += r
            if len(r) < bytes_left:
                self.seek(0)
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
        return self.page_size * self.pages_per_block * self.number_of_blocks

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

    def DumpFlashToFile(self, destination, start=0, end=-1):
        """Reads all pages from the flash, and writes it to a file.

        Args:
            destination(str): the destination file.
            start(int): Page to start dumping from.
            end(int): Page to stop dumping at. Go until the end if -1.
        Raises:
            errors.YandException: if no destination file is provided.
        """
        if not destination:
            raise errors.YandException('Please specify where to write')

        total_size = self.GetTotalSize()
        if end > 0:
            total_size = (end - start) * self.page_size
        else:
            end = self.GetTotalPages()

        if destination == "-":
            for page in range(start, end):
                sys.stdout.buffer.write(self.ReadPage(page))
        else:
            progress_bar = tqdm(
                total=total_size,
                unit_scale=True,
                unit_divisor=1024,
                unit='B'
            )
            with open(destination, 'wb') as dest_file:
                for page in range(start, end or self.GetTotalPages()):
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



    def EraseBlockByPage(self, page_number):
        """Erase the block containing a page.

        Args:
            page_number(int): the number of the page where we will erase the block.
        """
        block_address = page_number >> 8
        self.ftdi_device.write_protect = False
        self.SendCommand(self.NAND_CMD_ERASE)
        self.SendAddress(block_address, 3) # Is 3 always the case?
        self.SendCommand(self.NAND_CMD_ERASE_START)
        self.ftdi_device.WaitReady()
        self.ftdi_device.write_protect = True

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

    def Erase(self, start=0, end=-1):
        """Erase all blocks in the NAND Flash.

        Args:
            start(int): erase from this block number.
            end(int): erase up to this block. -1 means the end."""
        total_size = self.GetTotalSize()

        if end == -1:
            end = self.number_of_blocks

        if end > 0:
            total_size = (end - start) * self.page_size

        progress_bar = tqdm(
            total=total_size,
            unit_scale=True,
            unit_divisor=1024,
            unit='B'
        )
        for block in range(start, end):
            self.EraseBlock(block)
            progress_bar.update(self.page_size * self.pages_per_block)

    def FillWithValue(self, value, start=0, end=None):
        """Fill the NAND flash with a specific value.

        Args:
            value(int): the value to write.
            start(int): the first page to write.
            end(int): the last page to write.
        """
        total_size = self.GetTotalSize()

        if end > 0:
            total_size = (end - start) * self.page_size

        progress_bar = tqdm(
            total=total_size,
            unit_scale=True,
            unit_divisor=1024,
            unit='B'
        )
        for page in range(start, end or self.GetTotalPages()):
            self.WritePage(page, bytearray([value]*self.page_size))
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
                if page_number % self.pages_per_block == 0:
                    self.EraseBlockByPage(page_number)
                page_data = input_file.read(self.page_size)
                self.WritePage(page_number, page_data)
                progress_bar.update(self.page_size)
