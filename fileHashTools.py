# fileHashTools.py  

# Moved to github. History in commit messages.
# 1.1 Only import ProgressBar when needed. Better handling of file access errors. (Somewhat)
# 1.0 Shouldn't crash with unicode, but it's a bit of a crude fix. Unicode filenames
#	will only print correctly if the terminal is expecting encoded UTF-8 and if the 
#	filename is getting trimed, some unicode characters might break.
#	Also made progress not fail on zero length files.
# 0.9 Okay, actually made last change work now. Also md5 bugfix in printing
# 0.8 lol actually made method change possible
# 0.7 lol forgot to change 1 line of old code, slightly changed filename checking
# 0.6 changed to use proper option parser, new logging, hopefully progress bar, and use util package
# pre0.6 loldunno


# Default mode is to verify files. 
# If you do NOT specify a file(s) then program will check to see if there are checksums in the
# filenames of the current folder that match

# default method is CRC
# method ONLY applies to "filename checking" like the above example, AND when creating a checksum file.
# it does NOT apply when verfiying checksums in a file (because of extension .md5, .sfv, .crc)

#I don't suggest using absolute paths.
# before using it on megas files, test it on a small subset of test files in a test folder and whatnot.

from zlib import crc32
from sys import exit, platform
from os import getcwdu, listdir, walk, fsync, stat
from os.path import abspath, basename, exists, isabs, isdir, isfile, join, splitext, relpath
from hashlib import md5
from codecs import open as codopen
from shutil import copyfile
from optparse import OptionParser
try: 
	from util import buildpathlist, version, LogUtil, Console
	if version < 0.3: 
		print("util version too low. Need 0.3 or greater.")
		exit(1)
except:
	print("util.py missing or version too low. Need 0.3 or greater.")
	exit(1)
	
from logging import basicConfig, getLogger, DEBUG
basicConfig(level=DEBUG, format="%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y%m%d %H:%M:%S")
log = getLogger("FileHashTools")
	
#CRCregex = re.compile('\b[A-Fa-f0-9]{8}\b')
#matches = CRCregex.findall(string)

class Globals:
	verbose = False
	cwd = None
	tmpfile = None
	failed = 0
	passed = 0
	notfound = 0
	invalid = 0
	progress = False
	consolesize = 0
	options = None
	
class Hash:
	def __init__(self, chunk, method):
		self.method = method
		if method == "crc":
			self.hash = crc32(chunk)
		elif method == "md5":
			self.hash = md5(chunk)
	
	def update(self, chunk):
		if self.method == "crc":
			self.hash = crc32(chunk,self.hash)
		elif self.method == "md5":
			self.hash.update(chunk)
	
	def gibehex(self):
		if self.method == "crc":
			return format((self.hash & 0xffffffff),"08X")
		elif self.method == "md5":
			return self.hash.hexdigest()

def getsum(path, method):
	f = open(path,"rb")
	progress = None
	size = stat(path).st_size
	if Globals.progress and size != 0:
		widgets = ["%s" % Console.trimstring(basename(path).encode("utf-8")), Percentage(), ' ', Bar(left="[", right="]"), ' ', ETA()]
		progress = ProgressBar(term_width=Globals.consolesize, widgets=widgets, maxval=size).start()
	#lol arbitrary 2MB
	try: h = Hash(f.read(2097152), method)
	except Exception as e: 
		LogUtil.printlog("Error: %s in %s" % (e, path))
		return
	if Globals.progress and progress: progress.update(f.tell())
	try: chunk = f.read(2097152)
	except Exception as e: 
		LogUtil.printlog("Error: %s in %s" % (e, path))
		return
	if Globals.progress and progress: progress.update(f.tell())
	while chunk:
		h.update(chunk)
		try: chunk = f.read(2097152)
		except Exception as e: 
			LogUtil.printlog("Error: %s in %s" % (e, path))
			return
		if Globals.progress and progress: progress.update(f.tell())
	f.close()
	#if Globals.progress: progress.finish()
	if Globals.progress: Console.clearline()
	return h.gibehex()
			
def checkfile(path, method):
	checksum = getsum(path, method)
	if checksum in basename(path) or checksum in basename(path).upper():
		Globals.passed += 1
		if Globals.verbose:
			LogUtil.printlog("Found: %s in: %s" % (checksum, path))
	else:
		Globals.failed += 1
		LogUtil.printlog("Not found: %s in: %s" % (checksum,path))
	# crc32(data) & 0xffffffff	

def checkpath(path, method):
	if not exists(path): 
		log.warn("Not found: %s" % path)
		return
		
	if isdir(path):
		for fname in listdir(path):
			if isdir(join(path,fname)):
				LogUtil.printlog("--- DIR: %s ---" % fname)
				checkpath(join(path,fname), method)
				LogUtil.printlog("--- END ---")
			else:
				checkfile(join(path,fname), method)
	else:
		checkfile(path, method)


def compsum(fname, hash, mode):
	newhash = getsum(fname,mode)
	if hash != newhash:
		LogUtil.printlog("Hash mismatch: Expecting: %s got %s for %s" % (hash, newhash, fname))
		Globals.failed += 1
	else:
		if Globals.verbose: LogUtil.printlog("Hash match: Expecting: %s got %s for %s" % (hash, newhash, fname))
		Globals.passed += 1
	
def checksums(fname, method):
	f = codopen(fname,"rb","utf-8")
	mode = None
	if splitext(path)[1] == ".crc" or splitext(path)[1] == ".sfv":
		mode = "crc"
	else: mode = "md5"
	
	lineno = 0
	for line in f:
		if line.startswith("#") or line.startswith(";"):
			lineno += 1
			continue
		line = line.strip()
		hash = None
		if mode == "crc":
			try: fname, hash = line.rsplit(None, 1)
			except:	
				log.warn("Invalid line (%s): %s" % (lineno, line))
				Globals.invalid += 1
		else:
			try: hash, fname = line.split(None, 1)
			except:	
				log.warn("Invalid line (%s): %s" % (lineno, line))
				Globals.invalid += 1
		lineno += 1
		
		if isabs(fname):
			if exists(fname):
				compsum(fname,hash,mode)
			else:
				LogUtil.printlog("File not found: %s" % fname)
				Globals.notfound += 1
		else:
			if Globals.options.aster:
				if fname[0] == "*":
					fname = fname[1:]
			if exists(join(Globals.cwd, fname)):
				compsum(join(Globals.cwd, fname),hash,mode)
			else:
				LogUtil.printlog("File not found: %s" % fname)

def _getnextfname(method):
	if method == "crc":
		try: fname = Globals.tmpfile.next().rstrip().rsplit(None, 1)[0]
		except StopIteration: return "-EOF"
		return fname
	else:
		try: fname = Globals.tmpfile.next().rstrip().split(None, 1)[1]
		except StopIteration: return "-EOF"
		return fname

def printsum(path,method,cont=False):
	fname = None
	if cont:
		fname = _getnextfname(method)
	if isdir(path):
		#walk here
		for root, dirs, files in walk(path):
			for file in files:
				if cont:
					if fname == relpath(join(root,file)):
						log.debug("FOUND: %s" % fname)
						fname = _getnextfname(method)
						continue
					else:
						log.warn("NOT FOUND: %s is not %s" % (fname,relpath(join(root,file))))
						log.info("Continue from this point? y/(n):")
						yesno = input()
						if yesno != "y": 
							"Bailing..."
							exit()
						cont=False
				
				if method == "crc":
					LogUtil.printlog("%s %s" % (relpath(join(root,file)), getsum(join(root,file), method)))
				else:
					LogUtil.printlog("%s %s" % (getsum(join(root,file), method), relpath(join(root,file))))
	else:
		if method == "crc":
			LogUtil.printlog("%s %s" % (relpath(path), getsum(path,method)))
		else:
			LogUtil.printlog("%s %s" % (getsum(path,method), relpath(path)))

# ######################### #
Globals.cwd = getcwdu()
mode = "check"

parser = OptionParser(usage="usage: %prog [options] [dir[s]/drive[s]]")
parser.add_option("--verbose", action="store_true", dest="verbose", default=False,
	help="Enable printing verbose hash match messages.")
parser.add_option("-v", "--verify", dest="verify", action="store_true", default=True,
	help='Verify mode. Used to verify checksums')
parser.add_option("-c", "--create", dest="create", action="store_true", default=False,
	help="Create checksum file.")
parser.add_option("-p", "--progress", dest="progress", action="store_true", default=False,
	help="Show per file progress bar.")
#Not implementable yet with current tools
# parser.add_option("--total-progress", dest="totalprogress", action="store_true", default=False,
	# help="Show total progress. This will need to precalc size of things beforehand so can be sort of slow to get started.")
parser.add_option("-C", "--cont-create", dest="contcreate", action="store_true", default=False,
	help="Continue creating [MIGHT BE BROKEN AS HELL, hope your directory structure didn't change].")
parser.add_option("-m", "--method", dest="method", default="CRC", metavar="CRC|MD5",
	help="Method (CRC or MD5), default is CRC.")
parser.add_option("-o", "--output", dest="output", metavar="FILE", default=None,
	help="Output to this file.")
parser.add_option("--asterisk", dest="aster", action="store_true", default=False,
	help="MD5 file has * prefixed sums.")
parser.add_option("--quiet", dest="quiet", action="store_true", default=False,
	help="Don't print results to stdout. Only makes sense to use this with --output.")
(options, args) = parser.parse_args()

options.method = options.method.lower()
if options.method != "crc" and options.method != "md5":
	options.method = "crc"

if options.create:
	mode = "create"
	log.info("Creating...")
elif options.contcreate:
	mode = "Continue"
	if not options.output:
		log.error("Continue create doesn't really make sense without an output file. Bailing.")
		exit(1)
	log.warn("WARNING: ATTEMPING TO APPEND TO (%s). You should probably backup this file. \nPress button to continue." % options.output)
	input()
	copyfile(options.output, options.output+".tmp")
	Globals.tmpfile = codopen(options.output+".tmp", "r", "utf-8")
	LogUtil.f = codopen(options.output, "a", "utf-8")
else:
	log.info("Checking...")
	
if not options.contcreate:
	if options.output:
		if exists(options.output):
			log.warn("WARNING: OVERWRITE (%s)? (y/n)" % options.output)
			yesno = input()
			if yesno != "y": 
				log.info("Bailing...")
				exit()
		LogUtil.f = codopen(options.output, "w", "utf-8")

if options.verbose:
	Globals.verbose = True
if options.quiet:
	LogUtil.quiet = True
if options.progress: 
	try: from progressbar import ProgressBar, Percentage, Bar, Timer, ETA
	except: 
		print("You need this: http://pypi.python.org/pypi/progressbar")
		exit(1)
	Globals.progress = True

Globals.consolesize = Console.getconsolewidth()
#end options
Globals.options = options

paths = buildpathlist(args)
			
for path in paths:
	if mode == "create":
		printsum(path, options.method)
	elif mode == "Continue":
		printsum(path, options.method, cont=True)
	elif mode == "check":
		if isfile(path) and (splitext(path)[1] == ".md5" or splitext(path)[1] == ".crc" or splitext(path)[1] == ".sfv"):
			checksums(path, options.method)
		else:
			checkpath(path, options.method)

if Globals.passed or Globals.failed:
	log.info("Done. Passed: %s Failed: %s Not Found: %s Invalid: %s" % (Globals.passed, Globals.failed, Globals.notfound, Globals.invalid))
