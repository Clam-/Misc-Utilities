#STDIN helper

from sys import exit, stdin
from optparse import OptionParser
from codecs import open as codopen
from time import sleep
from threading import Thread
from queue import Queue
from subprocess import Popen, PIPE
from io import StringIO
from os import devnull, fdopen, fsync
from pty import openpty
class ReadStuff(Thread):
	def __init__(self, q, incoming):
		Thread.__init__(self)
		self.q = q
		self.iq = incoming
		
	def run(self):
		args = ["python", "-c", "while True: print raw_input()"]
		(master, slave) = openpty()
		sf = fdopen(slave, "r")
		mf = fdopen(master, "rw")
		p = Popen(args, stdout=slave, stdin=slave, stderr=open(devnull,"w")) #, stderr=open(devnull,"w")
		try:
			print(p.returncode)
			while p.returncode == None:
				line = mf.readline()
				print("a", line)
				# if line == "":
					# break
				# elif line == "STOP\n":
					# break
				# else:
				if not self.iq.empty():
					mf.write(self.iq.get())
					mf.flush()
					fsync(master)
					
				self.q.put(line.strip())
				sleep(0.2)
				p.poll()
				print(p.returncode)
			print("INPUT PROC CLOSED")
		except KeyboardInterrupt:
			print("WATHAPPEN")
		print("CLOSING INPUT THREAD")

parser = OptionParser(usage="usage: %prog [options] program [original program arguments]",
	epilog=''' ''')
parser.disable_interspersed_args()
parser.add_option("-i", "--input", dest="infile", metavar="INFILE",
	help="Read STDIN from INFILE")
parser.add_option("-n", "--no-stdin", dest="nostdin", 
	action="store_true", help="Do not read from STDIN")
parser.add_option("-s", "--wait", type="float", dest="wait", metavar="FLOAT",
	help="Wait for FLOAT seconds before passing STDIN to program")	
parser.add_option("--no-filefirst", dest="nofilefirst",
	action="store_true", help="Read STDIN from normal STDIN before file. (Default is read STDIN from file before normal STDIN)")
	
(options, args) = parser.parse_args()
if not args:
	print("MISSING PROGRAM TO LAUNCH (and it's params.) Exiting.")
	exit(1)

buff = []
if options.infile:
	try: f = codopen(options.infile, "r", "utf-8")
	except: 
		print("Unable to open file (%s) for reading. Exiting." % options.infile)
		exit(1)
	buff.append(f)
if not options.nostdin:
	if options.nofilefirst:
		buff.insert(0, stdin)
	else:
		buff.append(stdin)

if not options.wait:
	options.wait = 0

print("Starting input thread")
console = Queue()
tothread = Queue()
cons = ReadStuff(console, tothread)
cons.start()	

print("EXECUTING: %s" % " ".join(args))

p = Popen(args, stdin=PIPE)
sleep(options.wait)
p.poll()
for b in buff:
	p.stdin.write(b.read())
	p.poll()
#p.stdin = stdin
p.poll()
try:
	while p.returncode == None:
		if not console.empty():
			p.stdin.write(console.get()+"\n")
		sleep(0.2)
		p.poll()
except KeyboardInterrupt:
	tothread.put("\3")
print("WAITING FOR THREAD...")
p.wait()
print("DONE")