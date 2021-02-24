"""Classes for a FTDI device"""

from pyftdi import ftdi

from yand import errors

class FtdiDevice:
    """Class for a Ftdi Device."""

    DEFAULT_USB_VENDOR = 0x0403
    DEFAULT_USB_DEVICEID = 0x6010
    DEFAULT_INTERFACE_NUMBER = 1 # starts at 1

    def __init__(self):
        """Initializes a FtdiDevice object"""
        self.ftdi = None
        self.write_protect = True

    def Setup(self):
        """Sets up the FTDI device."""
        self.ftdi = ftdi.Ftdi()
        try:
            self.ftdi.open(
                self.DEFAULT_USB_VENDOR,
                self.DEFAULT_USB_DEVICEID,
                interface=self.DEFAULT_INTERFACE_NUMBER)
        except OSError:
            raise errors.YandException(
                'Could not open FTDI device\n'
                'Check USB connections')

        self.ftdi.set_bitmode(0, ftdi.Ftdi.BitMode.MCU)
        self.ftdi.write_data(bytearray([ftdi.Ftdi.DISABLE_CLK_DIV5]))
        self.ftdi.purge_buffers()
        self.ftdi.write_data(bytearray([ftdi.Ftdi.SET_BITS_HIGH, 0x0, 0x1]))
        self.WaitReady()

    def WaitReady(self):
        """Waits for the FTDI device to be ready.

        Raises:
            errors.YandException: if the device is not ready.
        """
        while 1:
            self.ftdi.write_data(bytearray([ftdi.Ftdi.GET_BITS_HIGH]))
            data = self.ftdi.read_data_bytes(1)
            if not data:
                data = self.ftdi.read_data_bytes(1)
                if not data:
                    raise errors.YandException('FTDI device not responding. Try restarting it.')
            if data[0]&2 == 0x2:
                break

    def Write(self, data, command=False, address=False):
        """Write a set of bytes to the device.

        Args:
            data(bytearray): the data to write.
            command(bool): if it is a command.
            address(bool): if it is an address.
        Raises:
            errors.YandException: if both command & address types are set.
        """
        cmd_type = 0
        if command and address:
            raise errors.YandException('Can\'t set command and address latch simultaneously')
        if command:
            cmd_type |= 0x40
        elif address:
            cmd_type |= 0x80
        if not self.write_protect:
            cmd_type |= 0x20

        cmds = [ftdi.Ftdi.WRITE_EXTENDED, cmd_type, 0, data[0]]
        for i in range(len(data)-1):
            cmds += [ftdi.Ftdi.WRITE_SHORT, 0, data[i+1]]
        self.ftdi.write_data(bytearray(cmds))

    def Read(self, size):
        """Reads a set of bytes from the device.

        Args:
            size(int): the amount of bytes to read.
        Returns:
            bytearray: the data.
        """
        cmds = [ftdi.Ftdi.READ_EXTENDED, 0, 0]
        for _ in range(size-1):
            cmds += [ftdi.Ftdi.READ_SHORT, 0]
        cmds.append(ftdi.Ftdi.SEND_IMMEDIATE)

        self.ftdi.write_data(cmds)

        data = self.ftdi.read_data(size)
        return data
