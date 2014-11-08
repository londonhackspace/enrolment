#!/usr/bin/env python

import os
import pygame
from pygame.locals import *
from pgu import gui
import time, serial, argparse, logging, threading, Queue, sys, traceback
from RFUID import rfid
from addcard import addCard

class cardReader(object):
	def __init__(self, queue, debugid):
		self.readerok = True
		try:
			# TODO: keep this reader for checkForCard
			with rfid.Pcsc.reader() as reader:
				logging.info('PCSC firmware: %s', reader.pn532.firmware())
		except (serial.SerialException, serial.SerialTimeoutException), e:
			logging.warn('Serial error during initialisation: %s', e)
			self.readerok = False
		except Exception, e:
			logging.critical('Unexpected error during initialisation: %s', e)
			self.readerok = False
		self.current = None
		self.queue = queue
		self.debugid = debugid
		
	def run(self):
		while True:
			if self.readerok:
				try:
					with rfid.Pcsc.reader() as reader:
						for tag in reader.pn532.scan():
							uid = tag.uid.upper()
				except rfid.NoCardException:
					self.current = None
					uid = None
			else:
				if self.debugid:
					uid = self.debugid
				else:
					uid = None

			if self.current and self.current == uid:
				pass
			elif uid:
				logging.info("Got card with uid %s", uid)
				self.queue.put_nowait(uid)
				pygame.event.post(pygame.event.Event(pygame.USEREVENT, card=uid))
				pygame.event.pump()
				self.current = uid

			time.sleep(2)

def timeout():
	pygame.event.post(pygame.event.Event(pygame.USEREVENT, timeout=True))
	pygame.event.pump()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--foreground', action='store_true')
    parser.add_argument('-i', '--id', type=str, nargs=1, help="a card uid (used for debugging if you don't have a reader handy)")
    args = parser.parse_args()
    return args

def set_logger():
    if True: #args.foreground:
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.DEBUG)
    else:
#        logfac = config.get('enrolement', 'logfacility')
	logfac = "user"
        logfac = SysLogHandler.facility_names[logfac]
        logger = logging.root
        logger.setLevel(logging.DEBUG)
        syslog = SysLogHandler(address='/dev/log', facility=logfac)
        formatter = logging.Formatter('Enrolement[%(process)d]: %(levelname)-8s %(message)s')
        syslog.setFormatter(formatter)
        logger.addHandler(syslog)
                                                                                 
class enroler:
	screen = None;
	def __init__(self, id):
		"Ininitializes a new pygame screen using the framebuffer"
		# Based on "Python GUI in Linux frame buffer"
		# http://www.karoltomala.com/blog/?p=679
		disp_no = os.getenv("DISPLAY")
		if disp_no:
			logging.info("I'm running under X display = {0}".format(disp_no))
			pygame.display.init()
			self.screen = pygame.display.set_mode((1280, 1024), 0, 16)
			size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
		else:
			# Check which frame buffer drivers are available
			# Start with fbcon since directfb hangs with composite output
			drivers = ['fbcon', 'directfb', 'svgalib']
			found = False
			for driver in drivers:
				# Make sure that SDL_VIDEODRIVER is set
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
			self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN, 16)
			# we don't use a mouse
			pygame.mouse.set_visible(False)
			pygame.event.set_grab(True)


		# Clear the screen to start
		self.screen.fill((0, 0, 0))
		# Initialise font support
		pygame.font.init()
		self.myfont = pygame.font.SysFont("Arial", 30)

		# Render the screen
		pygame.display.update()
		
		#
		# we can probably just use pygame events and lose the queue,
		# but leave it for now.
		#
		self.queue = Queue.Queue(42)
		self.cardreader = cardReader(self.queue, id)
		self.t = threading.Thread(name="cardreader", target=self.cardreader.run)
		self.t.setDaemon(True)
		self.t.start()

		self.state = 'saver'
		self.timeout = None
		self.success_time = None
 
		self.debugid = id
 
	def __del__(self):
		"Destructor to make sure pygame shuts down, etc."
		# do we really need this?

	def reset_timeout(self):
		# 5 min timeout for the screensaver
		if self.timeout:
			self.timeout.cancel()
		self.timeout = threading.Timer(60.0 * 5, timeout)
		self.timeout.setDaemon(True)
		self.timeout.start()

# todo
#
# Default : bouncy logo
#
# card swiped or key press -> hello
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
		self.reset_timeout()
		
		black = (0, 0, 0)
		white = (255, 255, 255)
		red = (255, 0, 0)
		green = (0, 255, 0)

		mytheme = gui.Theme('big_theme')

		app = gui.App(theme=mytheme)
		app.connect(gui.QUIT, app.quit, None)

		c = gui.Table(hpadding=4, vpadding=4)
		fg = white

		c.tr()
		logo = gui.Image("Hackspace_Wiki.png")
		c.td(logo, colspan=2)

		c.tr()
		c.td(gui.Label("Please login to add your card.", color=fg), colspan=2)

		c.tr()
		long = gui.Label("Use the same email and password that you used to register on the website.", color=fg)
		lw, lh = long.resize()
		c.td(long, colspan=2)

		c.tr()
		uid = None
		card_label = gui.Label("Please place an RFID card or token on the reader", color=fg)
		c.td(card_label, colspan=2)

		def activated():
			ers = [error1, error2, error3]
			for e in ers:
				e.set_text('')
				e.style.color = (255, 0, 0)
				e.repaint()
			app.update()
			app.paint()
			pygame.display.flip()

			uid = card_label.value.split()
			if len(uid) == 2:
				uid = uid[1]
			else:
				uid = None
			logging.info("adding card with uid %s for %s" % (uid, username.value))
			ac = addCard()
			ret, message = ac.add_card(username.value, password.value, uid)
			
			if ret:
				logging.info("Success!")
				self.state = "success"
				self.success_time = time.time() + 2.0
				self.reset_timeout()
				username.value = ''
				password.value = ''
				# goto success page, then timeout -> screensaver
				self.screen.fill(black)
				success.update()
				success.paint()
				pygame.display.flip()
			else:
				message = message.split('\n')
				for i,l in enumerate(message):
					if i < len(ers):
						ers[i].set_text(l)
						ers[i].repaint()

				app.update()
				app.paint()
				pygame.display.flip()
		
		def canceled():
			ers = [error1, error2, error3]
			for e in ers:
				e.set_text('')
				e.style.color = (255, 0, 0)
				e.repaint()
			username.value = ''
			password.value = ''
			card_label.set_text("Please place an RFID card or token on the reader")
			card_label.repaint()

			app.update()
			app.paint()
			pygame.display.flip()
			
			self.state = "saver"
			
		
		c.tr()
		c.td(gui.Label("Email: ", color=fg))
				
		username = gui.Input(value='', size=16)
		username.connect("activate", activated)
		c.td(username)
		
		c.tr()
		c.td(gui.Label("Password: ", color=fg))

		password = gui.Password(value='', size=16)
		password.connect("activate", activated)
		c.td(password)

		c.tr()
		login = gui.Button("Log in", color=fg)
		login.connect(gui.CLICK, activated)
		c.td(login, colspan=2, valign=-1)

		cancel = gui.Button("Cancel", color=fg)
		cancel.connect(gui.CLICK, canceled)
		c.td(cancel, colspan=2, valign=-1)

		c.tr()
		error1 = gui.Label(size=60, color=red)
		error1.blur()
		c.td(error1, colspan=2)

		c.tr()
		error2 = gui.Label(size=60, color=red)
		error2.blur()
		c.td(error2, colspan=2)

		c.tr()
		error3 = gui.Label(size=60, color=red)
		error3.blur()
		c.td(error3, colspan=2)

		tab_group = [username, password, login, cancel]
		tab_idx = 0
		tab_group[tab_idx].focus()
		
		app.init(c)

		success = gui.App(theme=mytheme)
		success.connect(gui.QUIT, success.quit, None)
		
		s = gui.Table(hpadding=4, vpadding=4)
		
		s.tr()
		logo = gui.Image("Hackspace_Wiki.png")
		s.td(logo, colspan=2)

		s.tr()
		s.td(gui.Label("Card successfully added!", color=green), colspan=2)
		
		success.init(s)
		
		uid = None
		while True:
			if self.state == 'saver':
				logging.info("screen saving")
				self.screen.fill(black)
				# blocks until something happens.
				self.screensaver()
				self.state = "awoken"
				# start out timeout again
				# so we go back into saver mode
				self.reset_timeout()

			try:
				uid = self.queue.get_nowait()
			except Queue.Empty:
				pass
			except Exception, e:
				logging.critical('Unexpected error during poll: %s', e)

			if uid:
				logging.info("card found: %s", uid)
				self.state = 'unknown card'
				text = "Card: " + uid
				self.screen.fill(black)
				card_label.set_text(text)
				card_label.repaint()
				app.update()
				app.paint()
				pygame.display.flip()
				self.reset_timeout()
				uid = None

#			for event in pygame.event.get():
			if True:
				event = pygame.event.wait()
				logging.info(event)
				self.reset_timeout()

				handled = False

				if self.state == "success":
					if self.success_time > time.time():
						success.update()
						success.paint()
						pygame.display.flip()
						# we don't want to handle the key up event from hitting
						# enter to activate the form!
						handled = True
					else:
						# some other key press, so back to the form.
						self.state = 'something'
					
				if event.type == pygame.QUIT:
					self.timeout.cancel()
					sys.exit()
				
				if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					self.timeout.cancel()
					sys.exit()

				if event.type == pygame.USEREVENT and 'timeout' in event.dict:
					self.state = 'saver'
					self.timeout.cancel()
					# no need to start it again if we are going back into saver mode

				if event.type == pygame.USEREVENT and 'card' in event.dict:
					uid = event.card

				if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
					tab_idx += 1
					if tab_idx >= len(tab_group):
						tab_idx = 0
					tab_group[tab_idx].focus()

					handled = True

				if not handled:
					app.event(event)

			if self.state != 'saver':
				# reset our timeout
				self.reset_timeout()

				if self.state == 'success' and self.success_time > time.time():
					# we don't want to handle the key up event from hitting
					# enter to activate the form!
					success.update()
					success.paint()
					pygame.display.flip()
				else:
					self.screen.fill(black)
					app.update()
					app.paint()
					pygame.display.flip()

#			time.sleep(0.2)

	def screensaver(self):
		# stop the timeout just incase it's running
		self.timeout.cancel()

		speed = [2, 2]
		
		size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
		width, height = size
		black = (0, 0, 0)

		ball = pygame.image.load("Hackspace_Wiki.png")
		ballrect = ball.get_rect()
		pygame.event.clear()
		while True:
			for event in pygame.event.get():
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						pygame.event.post(event)
					return
				elif event.type == pygame.USEREVENT:
					pygame.event.post(event)
					return
			
			ballrect = ballrect.move(speed)
			
			if ballrect.left < 0 or ballrect.right > width:
				speed[0] = -speed[0]
			if ballrect.top < 0 or ballrect.bottom > height:
				speed[1] = -speed[1]
				
			self.screen.fill(black)
			self.screen.blit(ball, ballrect)
			pygame.display.flip()
			time.sleep(0.05)

if __name__ == "__main__":
	args = parse_args()
	set_logger()

	if args.id:
		en = enroler(id=args.id[0])
	else:
		en = enroler(id=None)

	try:
		en.go()
	except Exception, e:
		logging.critical('Exception from go() %s', e)
		tb = traceback.format_exc()
		tb = tb.split('\n')
		for l in tb:
			logging.critical(l)
		if en.timeout:
			# otherwise we get stuck waiting for our thread to end.
			# should really setDaemon(True) somewhere?
			en.timeout.cancel()
