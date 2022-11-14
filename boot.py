import board
import digitalio
import storage
import time
import usb_cdc
import usb_midi

key = digitalio.DigitalInOut(board.GP2)
key.pull = digitalio.Pull.UP

if not key.value:
  led = digitalio.DigitalInOut(board.GP25)
  led.direction = digitalio.Direction.OUTPUT
  led.value = True
  time.sleep(1.0)
else:
  storage.disable_usb_drive()
  usb_midi.disable()
  usb_cdc.disable()
