#!/usr/bin/env python

from RFUID import rfid
import time, serial

def checkForCard():
  try:
    with rfid.Pcsc.reader() as reader:
      for tag in reader.pn532.scan():
        uid = tag.uid.upper()
        break
  except rfid.NoCardException:
    print "no card"
    return

#  if currentCard == uid:
#    return

  print "got card", uid
  time.sleep(2) # To avoid read bounces if the card is _just_ in range

try:
  # TODO: keep this reader for checkForCard
  with rfid.Pcsc.reader() as reader:
    print 'PCSC firmware: %s', reader.pn532.firmware()
except (serial.SerialException, serial.SerialTimeoutException), e:
  print 'Serial error during initialisation: %s' % (e)
except Exception, e:
  print 'Unexpected error during initialisation: %s' % (e)

try:
  while True:
    checkForCard()
    time.sleep(0.2)
except Exception, e:
  print 'Unexpected error during poll: %s' % (e)

