"""Module for a NAND device"""
import os
from pyftdi import ftdi
from tqdm import tqdm

from yand import errors


class NAND:
    """Class to operate on a NAND"""

    DEFAULT_USB_VENDOR = 0x0403
    DEFAULT_USB_DEVICEID = 0x6010
    DEFAULT_INTERFACE_NUMBER = 1 # starts at 1

    NAND_CMD_READ0 = 0x00
    NAND_CMD_PROG_PAGE_START = 0x10
    NAND_CMD_READSTART = 0x30
    NAND_CMD_ERASE = 0x60
    NAND_CMD_PROG_PAGE = 0x80
    NAND_CMD_READID = 0x90
    NAND_CMD_READ_PARAM_PAGE = 0xEC
    NAND_CMD_ERASE_START = 0xD0

    NAND_ADDR_ID = 0x00
    NAND_ADDR_ONFI = 0x20

    NAND_SIZE_ONFI = 0x100

    def __init__(self):
        """Initializes a NAND object"""
        self.ftdi_device = None

        # NAND geometry / config
        self.address_cycles = None
        self.device_manufacturer = None
        self.device_model = None
        self.manufacturer_id = None
        self.number_of_blocks = None
        self.oob_size = None
        self.page_size = None
        self.pages_per_block = None

        self.write_protect = True

    def GetTotalSize(self):
        """Returns the total size of the flash, in bytes"""
        return self.page_size * self.pages_per_block * self.number_of_blocks

    def GetTotalPages(self):
        """Returns the number of pages of the Flash."""
        return self.number_of_blocks * self.pages_per_block

    def GetInfos(self):
        """Returns a string showing NAND info"""
        return """Chip model & Manufacturer: {0:s} ({1:s})
Page Size : {2:d} ({3:d} + {4:d})
Blocks number : {5:d}
Device Size: {6:d}GiB
        """.format(
            self.device_model.strip(), self.device_manufacturer.strip(),
            self.page_size, (self.page_size - self.oob_size), self.oob_size,
            self.number_of_blocks,
            int(self.GetTotalSize() / 1024 / 1024 / 1024)
        )

    def _SetupFtdi(self):
        """Sets up the FTDI device."""
        self.ftdi_device = ftdi.Ftdi()
        try:
            self.ftdi_device.open(
                self.DEFAULT_USB_VENDOR,
                self.DEFAULT_USB_DEVICEID,
                self.DEFAULT_INTERFACE_NUMBER)
        except OSError as e:
            raise errors.YandException('Could not open FTDI device')

        self.ftdi_device.set_bitmode(0, ftdi.Ftdi.BITMODE_MCU)
        self.ftdi_device.write_data(bytearray([ftdi.Ftdi.DISABLE_CLK_DIV5]))
        # For 'slower mode':
        #self.ftdi_device.write_data(bytearray([ftdi.Ftdi.ENABLE_CLK_DIV5]))
        self.ftdi_device.set_latency_timer(ftdi.Ftdi.LATENCY_MIN)
        self.ftdi_device.purge_buffers()
        self.ftdi_device.write_data(bytearray([ftdi.Ftdi.SET_BITS_HIGH, 0x0, 0x1]))
        self.WaitReady()

    def _SetupFlash(self):
        """Setup the flash configuration."""

        # First we check if we can gather information form ONFI
        self.SendCommand(self.NAND_CMD_READID)
        self.SendAddress(self.NAND_ADDR_ONFI)
        onfi_available = ([0x4F, 0x4E, 0x46, 0x49] == self.ReadPage(4)) # ['O', 'N', 'F', 'I']

        if onfi_available:
            self.SendCommand(self.NAND_CMD_READ_PARAM_PAGE)
            self.SendAddress(self.NAND_ADDR_ID)
            self.WaitReady()
            onfi_data = self.ReadFlashData(self.NAND_SIZE_ONFI)
            self._ParseONFIData(onfi_data)
        else:
            raise errors.YandException(
                'Could not read ONFI info. Please provide your NAND geometry.')

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

        addr_cycles = onfi_data[101]
        self.address_cycles = (addr_cycles & 0x0f) + ((addr_cycles & 0xf0) >> 4)

    def Setup(self):
        """Sets the underlying IO and flash characteristics"""
        self._SetupFtdi()
        self._SetupFlash()

    def DumpFlashToFile(self, destination):
        """Reads all pages from the flash, and writes it to a file.

        Args:
            destination(str): the destination file.
        """
        if not destination:
            raise errors.YandException('Please specify where to write')
        bar = tqdm(
            total=self.GetTotalSize(),
            unit_scale=True,
            unit_divisor=1024,
            unit='B'
        )
        with open(destination, 'wb') as dest_file:
            for page in range(self.GetTotalPages()):
                dest_file.write(self.ReadPage(page))
                bar.update(self.page_size)

    def SendCommand(self, command):
        """Sends a command address to the NAND.

        Args:
            command(int): the command to send.
        """
        self._DeviceWrite(bytearray([command]), command=True)

    def WaitReady(self):
        """Waits for the device to be ready.

        Raises:
            errors.YandException: if the device is not ready.
        """
        while 1:
            self.ftdi_device.write_data(bytearray([ftdi.Ftdi.GET_BITS_HIGH]))
            data = self.ftdi_device.read_data_bytes(1)
            if not data:
                raise Exception('FTDI device not responding. Try restarting it.')
            if data[0]&2 == 0x2:
                break

    def ReadPage(self, page_number):
        """Returns the content of a page.

        Args:
            page_number(int): the page to read.
        Returns:
            bytearray: the content of the page.
        """
        page_address = page_number << 8
        # Send READ PAGE command
        self.SendCommand(self.NAND_CMD_READ0)
        self.SendAddress(page_address, self.address_cycles)
        self.SendCommand(self.NAND_CMD_READSTART)
        bytes_to_read = self.ReadFlashData(self.page_size)
        return bytes_to_read

    def ReadFlashData(self, size):
        """Reads the output of the NAND.

        Args:
            size(int): the number of bytes to read.
        Returns:
            bytearray: the data.
        """
        return self._DeviceRead(size)


    def SendAddress(self, address, size=1):
        """Writes an address to the NAND.

        Args:
            address(int): the address to set.
            size(int): the number LSB to send (ie: "address cycles").
        """
        data = (address).to_bytes(8, byteorder='little')
        self._DeviceWrite(data[0:size], address=True)

    def _DeviceWrite(self, data, command=False, address=False):
        """Write a set of bytes to the device.

        Args:
            command(bool): if it is a command.
            address(bool): if it is an address.
            data(bytearray): the data to write.
        """
        cmd_type = 0
        if command and address:
            raise errors.YandException('cant set command and address latch simultaneously')
        if command:
            cmd_type |= 0x40
        elif address:
            cmd_type |= 0x80
        if not self.write_protect:
            cmd_type |= 0x20

        cmds = [ftdi.Ftdi.WRITE_EXTENDED, cmd_type, 0, data[0]]
        for i in range(len(data)):
            cmds += [ftdi.Ftdi.WRITE_SHORT, 0, data[i+1]]
        self.ftdi_device.write_data(bytearray(cmds))

    def _DeviceRead(self, size):
        """Reads a set of bytes from the device.

        Args:
            size(int): the amount of bytes to read.
        Returns:
            bytearray: the data.
        """
        cmds = [ftdi.Ftdi.READ_EXTENDED, 0, 0]
        for _ in range(size):
            cmds += [ftdi.Ftdi.READ_SHORT, 0]
        cmds.append(ftdi.Ftdi.SEND_IMMEDIATE)

        data = self.ftdi_device.read_data(size)
        return data

    def EraseBlockByPage(self, page_number):
        """Erase the block containing a page.

        Args:
            page_number(int): the number of the page where we will erase the block.
        """
        block_address = page_number >> 8
        self.write_protect = False
        self.SendCommand(self.NAND_CMD_ERASE)
        self.SendAddress(block_address, 3) # Is 3 always the case?
        self.SendCommand(self.NAND_CMD_ERASE_START)
        self.WaitReady()
        self.write_protect = True

    def WritePage(self, page_number, data):
        """Writes a page to the NAND

        Args:
            page_number(int): the number of the page.
            data(bytearry): the data to program.
        """
        if not len(data) == self.page_size:
            raise errors.YandException(
                'Trying to write data that is different than page_size: {0:d} != {1:d}'.format(
                    len(data), self.page_size))
        self.write_protect = False

        page_address = page_number << 8

        self.SendCommand(self.NAND_CMD_PROG_PAGE)
        self.WaitReady()
        self.SendAddress(page_address, self.address_cycles)
        self.WaitReady()
        self._DeviceWrite(data)
        self.SendCommand(self.NAND_CMD_PROG_PAGE_START)
        self.WaitReady()

        self.write_protect = True

    def WriteFileToFlash(self, filename):
        """Overwrite file to Nand.

        Args:
            filename(str): path to the dump to write.
        """
        filesize = os.stat(filename).st_size
        if filesize > self.GetTotalSize():
            raise errors.YandException(
                'Input file is {0:d} bytes which is more than the current nand ({1:d})'.format(
                    filesize, self.GetTotalSize()))
        if filesize < self.GetTotalSize():
            print('WARNING: input file is {0:d} which is smaller than the current nand ({1:d})')


        bar = tqdm(
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
                bar.update(self.page_size)
