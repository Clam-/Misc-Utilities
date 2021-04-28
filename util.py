#util v0.4 - moved to github commit updatess
# 0.3 added size_to_human, fixed some tard bug
# 0.2 change print to unicodes
#nothing to run here

from sys import platform, stderr
from os import getcwd, listdir, environ
from os.path import isabs, dirname, abspath, exists, join

from codecs import open as codopen

from logging import getLogger
log = getLogger(__name__)

version = 0.5

def size_to_human(size, unit=1024, round=5):
	if size:
		unit_name = 'bytes'
		size=int(size)
		if size > unit:
			size = size/float(unit)
			unit_name = 'KiB'
		if size > unit:
			size = size/float(unit)
			unit_name = 'MiB'
		if size > unit:
			size = size/float(unit)
			unit_name = 'GiB'
		size = str(size)
		if round:
			if len(size) > round:
				size = size[0:round].rstrip(".")
		return size+unit_name
	else:
		return ""

class LogUtil:
	f = None
	quiet = False
	@staticmethod
	def printlog(s, d=1):
		#0 nothing, 1 print, 2 file, 3 both
		if not LogUtil.quiet: print(s.encode("utf-8"))
		if LogUtil.f: LogUtil.f.write('%s\n' % s)

def get_windows_term_width():
	from ctypes import create_string_buffer, windll
	csbi = create_string_buffer(22)
	if windll.kernel32.GetConsoleScreenBufferInfo(windll.kernel32.GetStdHandle(-12), csbi):
		from struct import unpack
		(bufx, bufy, curx, cury, wattr,
			left, top, right, bottom, maxx, maxy) = unpack("hhhhHhhhhhh", csbi.raw)
		sizex = right - left
	else:
		sizex = 80
	return sizex

class Console:
	width = None

	@staticmethod
	def getconsolewidth():
		if platform == "win32":
			Console.width = get_windows_term_width() - 1
			return Console.width
		else:
			Console.width = int(environ.get('COLUMNS', 80)) - 1
			return Console.width

	@staticmethod
	def clearline(f=stderr):
		if not Console.width:
			Console.getconsolewidth()
		f.write("\r%s\r" % (" "*Console.width))

	@staticmethod
	def trimstring(s):
		sizes = int(Console.width*(72/100.0))
		return s if len(s) <= sizes else s[:sizes-15]+"..."+s[-14:]

def buildpathlist(args, paths=None):
	if not paths:
		paths = []
	cwd = getcwd()

	if not args:
		paths.append(cwd)

	elif platform == "win32":
		from fnmatch import filter as fnfilter
		#make list of paths here

		dircontents = None

		for arg in args:
			if isabs(arg):
				if exists(arg):
					paths.append(str(arg))
				else:
					log.warn("Path not found: %s" % arg)

			elif exists(abspath(join(cwd,arg))):
				paths.append(join(cwd,arg))

			else:
				if not dircontents:
					dircontents = listdir(cwd)
				for fname in fnfilter(dircontents, arg):
					paths.append(join(cwd,fname))

	else:
		for arg in args:
			if isabs(arg):
				if exists(arg):
					paths.append(str(arg))
				else:
					log.warn("Path not found: %s" % arg)
			elif exists(abspath(join(cwd,arg))):
				paths.append(join(cwd,arg))

	return paths

#REQUIRE:
# * defaults must have all keys options has?
# * options SHOULD have all default=None
# * options MUST be in lowercase ~just because~
# * parser.add_option("--no-config", dest="noconf", action="store_true", default=None,
#		help='Do not attempt to read config file. Default is to always check for config.')
#   ^ THIS
# * parser.add_option("-c", "--config", dest="conf", default=None, metavar="CONFIGFILE",
#	help='Read from CONFIGFILE otherwise [scriptname].conf in script location.')
# anddd ^ THIS
def combine_options_fromfile(defaults, options, fname, scriptpath):
	fileoptions = {}
	scriptpath = dirname(abspath(scriptpath))
	if not options.noconf:
		fname = join(scriptpath, fname)
		if options.conf:
			fname = options.conf
		if exists(fname):
			for x in codopen(fname, "r", "utf-8"):
				x = x.strip()
				if x == "": continue
				elif x.startswith("#"): continue
				try: setting, value = x.split("=", 1)
				except ValueError: continue
				setting = setting.rstrip().lower()
				value = value.strip()
				if setting in defaults:
					if isinstance(defaults[setting], bool):
						fileoptions[setting] = value.lower() in ("true","1","t","yes")
					else:
						fileoptions[setting] = value
		else:
			if options.debug:
				log.warning("Config file (%s) not found." % fname)
	for option in defaults:
		if options.__dict__.get(option) == None:
			options.__dict__[option] = fileoptions.get(option, defaults[option])
