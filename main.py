#!/usr/bin/env python

import os
import pygame
from pygame.locals import *
from pgu import gui
import time, serial, argparse, logging, threading, Queue
from RFUID import rfid
from addcard import addCard

class cardReader(object):
	def __init__(self, queue):
		try:
			# TODO: keep this reader for checkForCard
			with rfid.Pcsc.reader() as reader:
				logging.info('PCSC firmware: %s', reader.pn532.firmware())
		except (serial.SerialException, serial.SerialTimeoutException), e:
			logging.warn('Serial error during initialisation: %s', e)
		except Exception, e:
			logging.critical('Unexpected error during initialisation: %s', e)
		self.current = None
		self.queue = queue
		
	def run(self):
		while True:
			try:
		  		with rfid.Pcsc.reader() as reader:
		  			for tag in reader.pn532.scan():
		  				uid = tag.uid.upper()
			except rfid.NoCardException:
				self.current = None
				uid = None

			if self.current and self.current == uid:
				pass
			elif uid:
				logging.info("Got card with uid %s", uid)
				self.queue.put_nowait(uid)
				pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"card": uid}))
				pygame.event.pump()
				self.current = uid

			time.sleep(2)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--foreground', action='store_true')
    args = parser.parse_args()
    return args

def set_logger():
    if args.foreground:
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.DEBUG)
    else:
        logfac = config.get('enrolement', 'logfacility')
        logfac = SysLogHandler.facility_names[logfac]
        logger = logging.root
        logger.setLevel(logging.DEBUG)
        syslog = SysLogHandler(address='/dev/log', facility=logfac)
        formatter = logging.Formatter('Enrolement[%(process)d]: %(levelname)-8s %(message)s')
        syslog.setFormatter(formatter)
        logger.addHandler(syslog)
                                                                                 
class enroler:
	screen = None;
	def __init__(self):
		"Ininitializes a new pygame screen using the framebuffer"
		# Based on "Python GUI in Linux frame buffer"
		# http://www.karoltomala.com/blog/?p=679
		disp_no = os.getenv("DISPLAY")
		if disp_no:
			logging.info("I'm running under X display = {0}".format(disp_no))
		# Check which frame buffer drivers are available
		# Start with fbcon since directfb hangs with composite output
		drivers = ['fbcon', 'directfb', 'svgalib']
		found = False
		for driver in drivers:
			# Make sure that SDL_VIDEODRIVER is set
			if not os.getenv('SDL_VIDEODRIVER'):
				os.putenv('SDL_VIDEODRIVER', driver)
			try:
				pygame.display.init()
			except pygame.error:
				logging.warn('Driver: {0} failed.'.format(driver))
				continue
			found = True
			logging.info("using %s", driver)
			break

		if not found:
			raise Exception('No suitable video driver found!')

		size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
		logging.info("Framebuffer size: %d x %d" % (size[0], size[1]))
		self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
		# Clear the screen to start
		self.screen.fill((0, 0, 0))
		# Initialise font support
		pygame.font.init()
		self.myfont = pygame.font.SysFont("Arial", 30)		

		# Render the screen
		pygame.display.update()
		pygame.mouse.set_visible(False)

		self.queue = Queue.Queue(42)
		self.cardreader = cardReader(self.queue)
		self.t = threading.Thread(name="cardreader", target=self.cardreader.run)
		self.t.setDaemon(True)
		self.t.start()

	def mkapp(self):
		pass
 
	def __del__(self):
		"Destructor to make sure pygame shuts down, etc."

# todo
#
# Default : bouncy logo
#
# card swiped -> hello
#
# if card_is_unknown():
#	if enrole():
# 		success()
#	else:
#		error()
# else:
#	fetch_user_details(uid)
#		# lol hah hah api on turing.
# 	print_things()
#
	def go(self):
		black = (0, 0, 0)
		self.screen.fill(black)
		self.screensaver()

		mytheme = gui.Theme('big_theme')

		app = gui.App(theme=mytheme)
		app.connect(gui.QUIT, app.quit, None)

		c = gui.Table()
		fg = (255, 255, 255)

		c.tr()
		logo = gui.Image("Hackspace_Wiki.png")
		c.td(logo, colspan=4)

		c.tr()
		c.td(gui.Label("Please login to add your card.", color=fg), colspan=2)

		c.tr()
		long = gui.Label("Use the same email and password that you used to register on the website.", color=fg)
		lw, lh = long.resize()
		c.td(long, colspan=2)

		c.tr()
		uid = None
		card_label = gui.Label("", color=fg)
		c.td(card_label, colspan=2)

		def activated():
			uid = card_label.value.split()[1]
			logging.info("adding card with uid %s for %s" % (uid, username.value))
			ac = addCard()
			if ac.add_card(username.value, password.value, uid):
				logging.info("Success!")
		
		c.tr()
		c.td(gui.Label("Email: ", color=fg))
				
		username = gui.Input(value='', size=12)
		username.connect("activate", activated)
		c.td(username, colspan=3)
		
		c.tr()
		c.td(gui.Label("Password: ", color=fg))

		password = gui.Password(value='', size=12)
		password.connect("activate", activated)
		c.td(password, colspan=3)

		c.tr()
		login = gui.Button("Log in", color=fg)
		login.connect(gui.CLICK, activated)
		c.td(login, colspan=4, align=-1)

		tab_group = [username, password, login]
		tab_idx = 0

		c2 = gui.Container(align=-1,valign=-1)
		left = (pygame.display.Info().current_w - lw) / 2
		c2.add(c, left, 20)
		
		tab_group[tab_idx].focus()
		
		app.init(c2)
		
		app.update()
		app.paint()
		pygame.display.flip()
		
		while True:
			uid = None
			changed = False
			try:
				uid = self.queue.get_nowait()
			except Queue.Empty:
				pass
			except Exception, e:
				logging.critical('Unexpected error during poll: %s', e)

			if uid:
				logging.info("card found: %s", uid)
				changed = True
				text = "Card: " + uid
				self.screen.fill(black)
				card_label.set_text(text)
				card_label.repaint()
				app.update()
				app.paint()
				pygame.display.flip()
				
#			for event in pygame.event.get():
			if True:
				event = pygame.event.wait()
				logging.info(event)

				handled = False

				if event.type == pygame.QUIT: sys.exit()

				if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
					tab_idx += 1
					if tab_idx >= len(tab_group):
						tab_idx = 0
					tab_group[tab_idx].focus()

					handled = True

				if not handled:
					app.event(event)

				changed = True

			if changed:
				self.screen.fill(black)
				app.update()
				app.paint()
				pygame.display.flip()

#			time.sleep(0.2)

	def screensaver(self):
		speed = [2, 2]
		
		size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
		width, height = size
		black = (0, 0, 0)

		ball = pygame.image.load("Hackspace_Wiki.png")
		ballrect = ball.get_rect()
		pygame.event.clear()
		while True:
			for event in pygame.event.get():
				print event
				if event.type == pygame.KEYDOWN:
					return
#			if pygame.event.peek():
#				return
			
			ballrect = ballrect.move(speed)
			
			if ballrect.left < 0 or ballrect.right > width:
				speed[0] = -speed[0]
			if ballrect.top < 0 or ballrect.bottom > height:
				speed[1] = -speed[1]
				
			self.screen.fill(black)
			self.screen.blit(ball, ballrect)
			pygame.display.flip()
			time.sleep(0.1)

if __name__ == "__main__":
	args = parse_args()
	set_logger()

	en = enroler()
	en.go()
