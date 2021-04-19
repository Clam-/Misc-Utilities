#tree printer? Path printer? dunno

#~90MB usage on 418GB of data spread out in 28,650 folders and 196,260 files

from sys import exit, argv, stdout, stderr
from os.path import basename, splitdrive, isdir, islink, isfile, join, exists
from os import stat, listdir
from optparse import OptionParser
try: 
	from util import buildpathlist, combine_options_fromfile, size_to_human, LogUtil, version, Console
	if version < 0.5: 
		print("util version too low. Need 0.5 or greater.")
		exit(1)
except ImportError:
	print("util.py missing or version too low. Need 0.5 or greater.")
	exit(1)
from logging import basicConfig, getLogger, DEBUG, INFO
basicConfig(level=INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y%m%d %H:%M:%S")
log = getLogger("treeprinter")

from codecs import open as codopen

try:
	import win32com.client 
except:
	print('''You need this: http://sourceforge.net/projects/pywin32/files/pywin32/ ''')
	print("You have Python version:", version)
	print("Make sure you get the right pywin32 for your Python version. (Read the readme on that page)")
	exit(1)

class ProgressWrapper:
	def __init__(self, progress):
		self.progress = progress
		self.total = 0
	def update(self, amount):
		self.total += amount
		try: self.progress.update(self.total)
		except: pass
	def finish(self):
		self.progress.finish()
	
class File:
	def __init__(self, name="", parent=None, size=0, modtime=0, createtime=0):
		self.name = name
		self.size = size
		self.modtime = modtime
		self.createtime = createtime
		self.parent = parent

class Dir(File):
	def __init__(self, name="", path="", size=0, modtime=0, createtime=0):
		File.__init__(self, name=name, size=size, modtime=modtime, createtime=createtime)
		self.dirs = []
		self.totaldirs = 0
		self.files = []
		self.totalfiles = 0
		self.path = path

class Drive:
	def __init__(self, name="", letter="", type="", fs="", serial="", size=0, free=0, used=0):
		self.name = name
		self.letter = letter
		self.fs = fs
		self.free = free
		self.totalsize = size
		self.serial = serial
		self.type = type
		self.stats = False
		self.dirs = []
		self.totaldirs = 0
		self.files = []
		self.totalfiles = 0
		self.size = used
		self.path = ""
		
def processdir(path, obj, progress=None):
	#path is a dir
	if islink(path):
		log.warn("Link ignored: %s" % path)
	elif isfile(path):
		log.error("Somehow I have a file here: %s" % path)
		exit(1)
	elif isdir(path):
		try:
			for fname in listdir(path):
				npath = join(path, fname)
				pathstat = stat(npath)
				if islink(npath):
					log.warn("Link ignored: %s" % npath)
					continue
				if isdir(npath): 
					obj.totaldirs += 1
					newdir = Dir(name=fname, path=npath, size=0, modtime=pathstat.st_mtime, createtime=pathstat.st_ctime)
					processdir(npath, newdir, progress)
					obj.dirs.append(newdir)
					obj.size += newdir.size
					obj.totaldirs += newdir.totaldirs
					obj.totalfiles += newdir.totalfiles
				elif isfile(npath):
					#print "FILE: %s" % npath
					size = pathstat.st_size
					if progress: progress.update(size)
					obj.files.append(File(name=fname, parent=obj, size=size, modtime=pathstat.st_mtime, createtime=pathstat.st_ctime))
					obj.totalfiles += 1
					obj.size += size
					#print obj.size
				else:
					log.warn("UNKNOWN OBJECT?? %s" % npath)
		except IOError as e:
			print(e)
			print("Directory access error, stats not accumulated for this directory.")
		except WindowsError as e:
			print(e)
			print("Folder access error, stats not accumulated for this folder.")
	else:
		log.warn("UNKNOWN OBJECT? %s" % path)


def start(path, drive, progress=None):
	st = stat(path)
	#preprocess to see if it's a drive or path we are dealing with
	if splitdrive(path)[1].lstrip("/\\"):
		#path not root
		if islink(path):
			log.warn("Link ignored: %s" % path)
		elif isdir(path):
			newdir = Dir(name=basename(path), path=path, size=0, modtime=st.st_mtime, createtime=st.st_ctime)
			drive.dirs.append(newdir)
			processdir(path, newdir, progress)
			drive.totaldirs += newdir.totaldirs
			drive.totalfiles += newdir.totalfiles
			drive.size += newdir.size
		elif isfile(path):
			size = st.st_size
			if progress: progress.update(size)
			drive.totalfiles += 1
			drive.files.append(File(name=basename(path), parent=drive, size=size, modtime=st.st_mtime, createtime=st.st_ctime))
			drive.size += size
		else:
			log.warn("UNKNOWN OBJECT? %s" % path)
	else:
		#root
		processdir(path, drive, progress)

def printtree(node, options, level):
	#if not dirfirst, combine lists
	#sort lists
	if options.depth >= 0 and level > options.depth:
		return
	combined = None
	if options.sortfirst:
		node.dirs.sort()
		node.files.sort()
		if options.dirfirst: combined = node.dirs+node.files
		else: combined = node.files+node.dirs
	else:
		if options.dirfirst: combined = node.dirs+node.files
		else: combined = node.files+node.dirs
		combined.sort()
	prefix = options.indent*level
	
	#{name} #{size} #{modtime} #{createtime}
	for item in combined:
		if options.minsize and (item.size < options.minsize): continue
		if options.maxsize and (item.size > options.maxsize): continue
		size = item.size if not options.human else size_to_human(item.size, round=options.rounding)
		if isinstance(item, Dir):
			#recurse
			if not options.nodirs:
				if options.dirnamebefore:
					LogUtil.printlog(options.dir.format(name=item.name, path=item.path, size=size, modtime=item.modtime,
						createtime=item.createtime, prefix=prefix))
			printtree(item, options, level+1)
			if not options.nodirs:
				if not options.dirnamebefore:
					LogUtil.printlog(options.dir.format(name=item.name, path=item.path, size=size, modtime=item.modtime,
						createtime=item.createtime, prefix=prefix))
		else:
			if not options.nofiles:
				#print stats
				LogUtil.printlog(options.file.format(name=item.name, path=item.parent.path, size=size, modtime=item.modtime,
					createtime=item.createtime, prefix=prefix))
	
defaults = {
	"all" : False,
	"indent" : " - ",
	"nofiles" : False,
	"nodirs" : False,
	"output": None,
	"human" : False,
	"rounding" : "5",
	"dirfirst" : False,
	"sortfirst" : True,
	"dirnamebefore" : True,
	"file" : "{prefix}{size} {name}",
	"dir" : "{prefix}{size} {path}\\{name}\\",
	"drivehead" : "Drive {letter} [{name}] Serial: {serial} Used: {size} (Dirs: {totaldirs}, Files: {totalfiles})",
	"drivefoot" : "",
	"debug" : False,
	"depth" : None,
	"minsize" : None,
	"maxsize" : None,
	"progress" : False,
	"quiet" : False,
	"sortby" : "name"
}
	
parser = OptionParser(usage="usage: %prog [options] [dir[s]/drive[s]]")
parser.add_option("-a", "--all", action="store_true", dest="all", default=None,
	help="By default if no drives/dirs are specified, it will only scan current folder on current drive.")
parser.add_option("-i", "--indent", dest="indent", default=None,
	help='String to use for each level of indentation. String is repeated for each nested folder. Default: " - "')
parser.add_option("--no-files", dest="nofiles", action="store_true", default=None,
	help="Don't display files.")
parser.add_option("--no-dirs", dest="nodirs", action="store_true", default=None,
	help="Don't display dirs.")
parser.add_option("-o", "--output", dest="output", default=None, metavar="OUTFILE",
	help='Log output to file, as well as standard output. This does not log errors.')
parser.add_option("--quiet", dest="quiet", action="store_true", default=None,
	help="Don't print results to stdout. Only makes sense to use this with --output.")
parser.add_option("--no-config", dest="noconf", action="store_true", default=None,
	help='Do not attempt to read config file. Default is to always check for config.')
parser.add_option("-c", "--config", dest="conf", default=None, metavar="CONFIGFILE",
	help='Read from CONFIGFILE otherwise [scriptname].conf in script location.')
parser.add_option("-s", "--human-readable", dest="human", action="store_true", default=None,
	help='Use human readable sizes. MiB, KiB, etc...')
parser.add_option("--rounding", dest="rounding", default=None, metavar="ROUNDTO", 
	help='How many characters to truncate when human readable. Default: 5')
parser.add_option("--dir-first", dest="dirfirst", action="store_true", default=None,
	help="Display dir's before files. Default is not to do this.")
parser.add_option("--no-sort-first", dest="sortfirst", action="store_true", default=None,
	help="Sort dirs and files after merging into a single list, instead of sorting them seperately. Default is to sort seperately.")
parser.add_option("--no-dir-name-first", dest="dirnamebefore", action="store_true", default=None,
	help="Show dirname after showing it's contents first. Default is to show the dirname before showing it's contents.")
parser.add_option("--file-entry", dest="file", metavar="FILETEXT", default=None,
	help="Template string for file entries.")
parser.add_option("--dir-entry", dest="dir", metavar="DIRTEXT", default=None,
	help="Template string for dir entries.")
parser.add_option("--drive-header", dest="drivehead", metavar="DRIVERHEADER", default=None,
	help="Template string for start of drive.")
parser.add_option("--drive-footer", dest="drivefoot", metavar="DRIVEFOOTER", default=None,
	help="Template string for end of drive.")
parser.add_option("--progress", dest="progress", action="store_true", default=None,
	help="Show progress per drive. This is only accurate when processing whole drive.")
parser.add_option("--max-depth", dest="depth", metavar="DEPTH", default=None,
	help="To what depth of nesting will be displayed. By default this is infinite, but if you need to overrite your config, you can use -1 to mean the same.")
parser.add_option("--min-size", dest="minsize", metavar="SIZE", default=None,
	help="Files/dirs will need to be at least this big before being printed. Size is in bytes. Default: no limit. If you need to overrite your config, you can use 0 to mean the same.")
parser.add_option("--max-size", dest="maxsize", metavar="SIZE", default=None,
	help="Files/dirs will need to be at most this big before being printed. Size is in bytes. Default: no limit. If you need to overrite your config, you can use 0 to mean the same.")
parser.add_option("--sort-by", dest="sortby", default=None,
	help="Sort by one of the following: name size. Default: name")
parser.add_option("--debug", dest="debug", default=None,
	help="Print some debug infos. 0=nothing 1=print 2=file 3=both")

(options, args) = parser.parse_args()
#grab defaults from file, and then override with commandlines.

combine_options_fromfile(defaults, options, "treeprinter.conf", __file__)

if options.output:
	LogUtil.f = codopen(options.output, "w", "utf-8")

if options.debug:
	log.level=DEBUG
	
try: options.rounding = int(options.rounding)
except: 
	log.warn("Rounding not int, using default: 5")
	options.rounding = int(defaults["rounding"])
if options.depth:
	try: options.depth = int(options.depth)
	except:
		log.warn("Max depth not int, using default: none (-1)")
		options.depth = -1
else: options.depth = -1
if options.minsize:
	try: options.minsize = int(options.minsize)
	except:
		log.warn("Min size not int, using default: none (0)")
		options.minsize = None
else: options.minsize = None
if options.maxsize:
	try: options.maxsize = int(options.maxsize)
	except:
		log.warn("Max size not int, using default: none (0)")
		options.maxsize = None
else: options.maxsize = None

if options.sortby != "name" or options.sortby != "size":
	log.warn("Invalid --sort-by value (%s). Using name." % repr(options.sortby))
	options.sortby = "name"

if options.quiet:
	LogUtil.quiet = True
	
if options.progress:
	try: from progressbar import AnimatedMarker, ProgressBar, Percentage, Bar, Timer, ETA
	except: 
		print("You need this: http://pypi.python.org/pypi/progressbar")
		exit(1)
	consolesize = Console.getconsolewidth()

#END OPTION CRAP

drives = {}
#populate drive info here
result = win32com.client.Dispatch("WbemScripting.SWbemLocator").ConnectServer(".", "root\cimv2").ExecQuery("Select * from Win32_LogicalDisk")
for drive in result: 
	if drive.Access == None:
		log.debug("Skipping drive: %s" % drive.Caption)
		continue
	if drive.Caption in drives:
		print("THIS SHOULDN'T HAPPEN")
		exit(1)
	drives[drive.Caption] = Drive(name=drive.VolumeName, letter=drive.Caption, type=drive.Description, fs=drive.FileSystem,
		serial=int(drive.VolumeSerialNumber, 16), size=int(drive.Size), free=int(drive.FreeSpace))

if options.all:
	#do everythings here, don't even care what folders person put
	paths = []
	for drive in drives:
		paths.append(drive+"\\")
else:
	#else only care about folders specified
	paths = buildpathlist(args)

for path in paths:
	drive, rest = splitdrive(path)
	drive = drives[drive.upper()]
	drive.stats = True
	progress = None
	if options.progress:
		#allow progress
		if not rest.lstrip("/\\"):
			widgets = ["Reading %s" % drive.letter, Percentage(), ' ', Bar(left="[", right="]"), ' ', ETA()]
			progress = ProgressWrapper(ProgressBar(term_width=consolesize, widgets=widgets, maxval=drive.totalsize-drive.free).start())
		else:
			widgets = ["Reading %s " % drive.letter, AnimatedMarker(), ' ', Timer()]
			progress = ProgressWrapper(ProgressBar(term_width=consolesize, widgets=widgets, maxval=drive.totalsize-drive.free).start())
	start(path, drive, progress)
	if progress: progress.finish()
	
#do final printing stuff here I guess
for drive in sorted(drives.keys()):
	if drives[drive].stats:
		d = drives[drive]
		#{name}{letter}{fs}{free}{totalsize}{serial}{type}{stats}{size}
		size = d.size if not options.human else size_to_human(d.size)
		if options.drivehead:
			LogUtil.printlog(options.drivehead.format(name=d.name, letter=d.letter, fs=d.fs, free=d.free, totalsize=d.totalsize,
				serial=d.serial, type=d.type, stats=d.stats, size=size, totaldirs=d.totaldirs, totalfiles=d.totalfiles))
		printtree(d, options, 0)
		if options.drivefoot:
			LogUtil.printlog(options.drivefoot.format(name=d.name, letter=d.letter, fs=d.fs, free=d.free, totalsize=d.totalsize,
				serial=d.serial, type=d.type, stats=d.stats, size=size, totaldirs=d.totaldirs, totalfiles=d.totalfiles))
