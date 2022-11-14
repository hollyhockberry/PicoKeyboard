# Copyright (c) 2022 Inaba (@hollyhockberry)
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php

import time
import alarm
import board
import displayio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from picocaptouch import ePaper29

epd = ePaper29()
kb = Keyboard(usb_hid.devices)
cc = ConsumerControl(usb_hid.devices)

epd.init(True)

if alarm.wake_alarm is None:
  g = displayio.Group()
  with open("/panel.bmp", "rb") as f:
    pic = displayio.OnDiskBitmap(f)
    t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    g.append(t)
    epd.display.show(g)
    epd.display.refresh()

touch = False
touch_time = None
last_time = time.monotonic()
point = None

def find(pos, term):
  keys = [
    ((0, 0), None, 'mute'),
    ((64, 0), None, 'vol-down'),
    ((128, 0), None, 'vol-up'),
    ((0, 64), None, 'rwd'),
    ((64, 64), None, 'play'),
    ((128, 64), None, 'fwd'),
    ((232, 0), 0.5, 'sleep'),
    ((232, 64), None, 'mirror')]

  def inRange(p, o):
    r = lambda x: o[x] <= p[x] and p[x] < (o[x] + 64)
    return r(0) and r(1)

  for (p, t, k) in keys:
    t = 0.01 if t is None else t
    if inRange(pos, p):
      if term < t:
        continue
      if k == 'mute':
        cc.send(ConsumerControlCode.MUTE)
      if k == 'vol-down':
        cc.send(ConsumerControlCode.VOLUME_DECREMENT)
      if k == 'vol-up':
        cc.send(ConsumerControlCode.VOLUME_INCREMENT)
      if k == 'rwd':
        cc.send(ConsumerControlCode.REWIND)
      if k == 'play':
        cc.send(ConsumerControlCode.PLAY_PAUSE)
      if k == 'fwd':
        cc.send(ConsumerControlCode.FAST_FORWARD)
      if k == 'sleep':
        kb.press(Keycode.COMMAND, Keycode.ALT)
        cc.send(ConsumerControlCode.EJECT)
        kb.release_all()
      if k == 'mirror':
        kb.press(Keycode.COMMAND)
        cc.send(ConsumerControlCode.BRIGHTNESS_DECREMENT)
        kb.release_all()

while True:
  points = list(epd.is_touch())
  if len(points) > 0:
    point = points[0]
    last_time = time.monotonic()
  elif time.monotonic() - last_time > 5 * 60:
    pin_alarm = alarm.pin.PinAlarm(pin=board.GP17, value=False, pull=True)
    alarm.exit_and_deep_sleep_until_alarms(pin_alarm)

  if not touch == (len(points) > 0):
    touch = not touch

    if not touch:
      find(point, time.monotonic() - touch_time)

    touch_time = time.monotonic() if touch else None
