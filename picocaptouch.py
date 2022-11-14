# Copyright (c) 2022 Inaba (@hollyhockberry)
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php

import time
import board
import busio
import digitalio
import displayio

_START_SEQUENCE = (
    b"\x12\x80\x14"  # soft reset and wait 20ms
    b"\x11\x01\x03"  # Ram data entry mode
    b"\x3C\x01\x05"  # border color
    b"\x2c\x01\x36"  # Set vcom voltage
    b"\x03\x01\x17"  # Set gate voltage
    b"\x04\x03\x41\x00\x32"  # Set source voltage
    b"\x4e\x01\x01"  # ram x count
    b"\x4f\x02\x00\x00"  # ram y count
    b"\x01\x03\x00\x00\x00"  # set display size
    b"\x44\x02\x01\x10" # _SSD1680_SET_RAMXPOS
    b"\x45\x04\x00\x00\x00\x00" # _SSD1680_SET_RAMYPOS
    b"\x22\x01\xf4"  # display update mode
)

_STOP_SEQUENCE = b"\x10\x81\x01\x64"  # Deep Sleep

class SSD1680(displayio.EPaperDisplay):
  def __init__(self, bus: displayio.Fourwire, **kwargs):
    stop_sequence = bytearray(_STOP_SEQUENCE)
    try:
      bus.reset()
    except RuntimeError:
      # No reset pin defined, so no deep sleeping
      stop_sequence = b""

    start_sequence = bytearray(_START_SEQUENCE)
    width = kwargs["width"]
    height = kwargs["height"]
    if "rotation" in kwargs and kwargs["rotation"] % 180 != 90:
        width, height = height, width
    start_sequence[29] = (width - 1) & 0xFF
    start_sequence[30] = ((width - 1) >> 8) & 0xFF
    start_sequence[40] = (width - 1) & 0xFF
    start_sequence[41] = ((width - 1) >> 8) & 0xFF

    super().__init__(
      bus,
      start_sequence,
      stop_sequence,
      **kwargs,
      ram_width=250,
      ram_height=296,
      busy_state=True,
      write_black_ram_command=0x24,
      write_color_ram_command=0x26,
      black_bits_inverted=False,
      # set_column_window_command=0x44,
      # set_row_window_command=0x45,
      set_current_column_command=0x4E,
      set_current_row_command=0x4F,
      refresh_display_command=0x20,
      colstart=1,
      always_toggle_chip_select=True,
    )


class ICNT86:
  def __init__(self, rotation):
    self.rotation = rotation
    self.address = 0x48
    self.i2c = busio.I2C(board.GP7, board.GP6)
    self.trst = digitalio.DigitalInOut(board.GP16)
    self.trst.direction = digitalio.Direction.OUTPUT

  def init(self, reset):
    while not self.i2c.try_lock():
      pass

    if reset:
      self.trst.value = 1
      time.sleep(0.1)
      self.trst.value = 0
      time.sleep(0.1)
      self.trst.value = 1
      time.sleep(0.1)

  def is_touch(self):
      def convert(x, y):
        if self.rotation == 0:
          return (x, y)
        if self.rotation == 90:
          return (y, 128 - x)
        if self.rotation == 180:
          return (128- x, 296 - y)
        if self.rotation == 270:
          return (296 - y, x)
        raise Exception

      b = self.readbytes(0x1001, 1)
      if b[0] > 0x00:
        t = b[0]
        b = self.readbytes(0x1002, t * 7)
        i = 0
        for i in range(0, t, 1):
          if b[5 + 7*i] > 0:
            x = 127 - ((b[4 + 7*i] << 8) + b[3 + 7*i])
            y = ((b[2 + 7*i] << 8) + b[1 + 7*i])
            yield convert(x, y)
      self.writebyte(0x1001, 0)
      time.sleep(0.01)

  def writebyte(self, reg, value):
    b = [(reg>>8) & 0xff, reg & 0xff, value]
    self.i2c.writeto(self.address, bytearray(b))

  def write(self, reg):
    b = [(reg>>8) & 0xff, reg & 0xff]
    self.i2c.writeto(self.address, bytearray(b))

  def readbytes(self, reg, len):
    self.write(reg)
    b = bytearray(len)
    self.i2c.readfrom_into(self.address, b)
    return b


class ePaper29:
  def __init__(self, rotation=270):
    displayio.release_displays()

    spi = busio.SPI(clock=board.GP10, MOSI=board.GP11)
    epd_cs = board.GP9
    epd_dc = board.GP8
    epd_reset = board.GP12
    epd_busy = board.GP13

    display_bus = displayio.FourWire(
        spi,
        command=epd_dc,
        chip_select=epd_cs,
        reset=epd_reset,
        baudrate=1000000
    )

    self.display = SSD1680(
      display_bus,
      width=296,
      height=128,
      busy_pin=epd_busy,
      highlight_color=0xFF0000,
      rotation=rotation
    )

    self._icnt86 = ICNT86(rotation)

    self.k0 = digitalio.DigitalInOut(board.GP2)
    self.k0.pull = digitalio.Pull.UP
    self.k1 = digitalio.DigitalInOut(board.GP3)
    self.k1.pull = digitalio.Pull.UP
    self.k2 = digitalio.DigitalInOut(board.GP15)
    self.k2.pull = digitalio.Pull.UP

  def init(self, reset):
    self._icnt86.init(reset)

  def is_touch(self):
    return self._icnt86.is_touch()
  
  def key(self):
    return (1 if not self.k0.value else 0) | \
           (2 if not self.k1.value else 0) | \
           (4 if not self.k2.value else 0)
