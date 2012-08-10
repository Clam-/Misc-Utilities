#email module
#stolen and modified from http://stackoverflow.com/questions/73781/

from email.mime.text import MIMEText
from subprocess import Popen, PIPE

from Queue import Queue
from threading import Thread, Event
from time import time, sleep
from datetime import date

from logging import getLogger
log = getLogger("emailmodule")

class Mailer(Thread):
	def __init__(self, sourcename="unknown", toaddr="localhost", subject="Error", fromaddr="localhost"):
		Thread.__init__(self)
		self.toaddr = toaddr
		self.fromaddr = fromaddr
		self.subject = subject
		self.messages = Queue()
		self.quitevent = Event()
		self.sourcename = sourcename
		#self.daemon = True
	
	def checkandsend(self):
		log.info("Starting checkandsend")
		items = []
		item = self.messages.get()
		if not item: return 1
		items.append(item)
		n = 1
		t = time()
		while time()-5 < t:
			while not self.messages.empty():
				item = self.messages.get()
				n += 1
				if not item: break
				items.append(item)
			sleep(0.5)
		
		log.info("Preparing to send mail")
		msg = MIMEText("Error(s) happen:\n%s" % "".join(items))
		msg["From"] = self.fromaddr
		msg["To"] = self.toaddr
		msg["Subject"] = "[%s] %s - %s" % (self.sourcename, date.today(), self.subject)
		p = Popen(["/usr/sbin/sendmail", "-t"], stdin=PIPE, stdout=PIPE)
		log.info("Calling sendmail")
		p.communicate(msg.as_string())
		log.info("Mail sent")
		return n
	

	def run(self):
		delay = 60
		lastrun = time()
		factor = 2
		while not self.quitevent.is_set():
			t = time()
			if t > lastrun + delay:
				for x in range(self.checkandsend()): self.messages.task_done()
				diff = t - lastrun
				lastrun = t
				if diff-5 < delay: #if within 5 seconds of trigger, then factor up
					if factor < 60: factor = factor * 2
				else:
					if factor > 2: factor = factor / 2
				delay = 60 * factor
			sleep(0.5)
		if not self.messages.empty(): 
			for x in range(self.checkandsend()): self.messages.task_done()
	
	def addmessage(self, msg):
		self.messages.put(msg)
	
	def quit(self):
		self.messages.put(None)
		self.quitevent.set()
		self.messages.join()
		