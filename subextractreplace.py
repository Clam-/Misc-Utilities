#subextractreplace v0.9

#run python subextractreplace -h for helps

#requires util.py >=0.5

# 0.2 Griff2.0-edit
# 0.3 attempt dum unicodes handling
# 0.4 proper path unicodes works now, probably, hopefully.
# 0.5 call extractsub on .mkv files onry (pls no japans pls)
# 0.6 fix previous thing so actually does it this time. Promise.
# 0.7 Implemented remuxing. Probably 100 bugs.
# 0.8 Changing subextractreplace to use new util, and hopefully better logging, and some bugfixes
# 0.9 Allow for replacement text being nothing to "remove" words, also made oldfile actually _old

from optparse import OptionParser
try: 
	from util import buildpathlist, version, combine_options_fromfile
	if version < 0.5: 
		print("util version too low. Need 0.5 or greater.")
		exit(1)
except ImportError:
	print("util.py missing or version too low. Need 0.5 or greater.")
	exit(1)
	

from os.path import isdir, exists, join, splitext, isabs, split
from os import getcwd, walk, chdir, mkdir
from shutil import rmtree, move
from subprocess import Popen, PIPE, STDOUT
from io import StringIO
from re import compile as recompile
from codecs import open as codopen

from logging import basicConfig, getLogger, DEBUG, INFO
basicConfig(level=INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
log = getLogger("subextractreplace")

class TrackThings:
	regexTrack = recompile(r"\|  \+ Track number\: ([0-9]+)")
	regexDefault = recompile(r"\|  \+ Default flag\: ([01])")
	regexCodec = recompile(r"\|  \+ Codec ID\: (.+)")
	regexLang = recompile(r"\|  \+ Language\: ([a-z]{3})")
	regexName = recompile(r"\|  \+ Name\: (.*)")
	regexTitle = recompile(r"\| \+ Title\: (.*)")
	regexSegUID = recompile(r"\| \+ Segment UID\: (.*)")
	subtemplate = '"--language" "0:{lang}" "--track-name" "0:{trackname}" "--default-track" "0:{default}" "--forced-track" "0:no" "-s" "0" "-D" "-A" "-T" "--no-global-tags" "--no-chapters" "{fname}"'
	regexCRC = recompile(r"[^a-zA-Z0-9][a-fA-F0-9]{8}[^a-zA-Z0-9]")
	
class Track:
	def __init__(self, num=None):
		self.num = num
		self.lang = "eng"
		self.default = True
		self.subs = False
		self.name = None

def runcommand(command, getoutput=False):
	log.debug("Executing: %s" % command)
	if getoutput:
		proc = Popen(command, stdout=PIPE, stderr=STDOUT)
		output = StringIO()
		while proc.returncode == None:
			output.write(proc.stdout.read())
			proc.poll()
		output.write(proc.stdout.read())
		if proc.returncode != 0:
			log.critical("Something bad happen.")
			exit(1)
		return output
	else:
		p = Popen(command)
		p.wait()
		if p.returncode == None:
			log.critical("Command should have been completed. Bailing.")
			exit(1)
		elif p.returncode > 0:
			log.critical("Command returned error: %s" % p.returncode)
		elif p.returncode < 0:
			log.critical("Command forced close? Returned: %s" % p.returncode)
		
		
def _getsublist(s):
	s.seek(0)
	subs = []
	mode = None
	track = None
	fileinfo = {}
	
	for line in s:
		line = line.strip()
		if line == "|+ Segment tracks": 
			mode = 0
			continue
		elif line == "|+ Segment information": 
			mode = 2
			continue
		if mode == 2:
			m = TrackThings.regexTitle.match(line)
			if m:
				fileinfo["title"] = m.group(1)
			m = TrackThings.regexSegUID.match(line)
			if m:
				fileinfo["SegUID"] = m.group(1)
		elif mode == 0:
			if line == "| + A track":
				#start of new track, append old track if subs
				if track and track.subs: subs.append(track)
				track = Track()
				continue
			elif not line.startswith("|  "): 
				mode = None
				continue
			#from here on out, assume track of any kind.
			m = TrackThings.regexTrack.match(line)
			if m:
				track.num = int(m.group(1))-1
				continue
			if line == '|  + Track type: subtitles': track.subs = True
			m = TrackThings.regexDefault.match(line)
			if m:
				if m.group(1) == "1": track.default = True
				else: track.default = False
				continue
			m = TrackThings.regexCodec.match(line)
			if m:
				ext = m.group(1)
				if "VOBSUB" in ext: track.ext = "."
				elif "TEXT/UTF8" in ext: track.ext = ".srt"
				elif "/ASS" in ext: track.ext = ".ass"
				else: track.ext = ""
				continue
			m = TrackThings.regexLang.match(line)
			if m:
				track.lang = m.group(1)
				continue
			m = TrackThings.regexName.match(line)
			if m:
				track.name = m.group(1)
				continue
	if track and track.subs: subs.append(track)
	return (subs, fileinfo)
			

def replacesubtext(oldfile, newfile, replacements):
	f = codopen(oldfile, "r", "utf-8")
	fn = codopen(newfile,"w", "utf-8")
	
	for line in f:
		for rep in replacements:
			if len(rep) < 2:
				orig, new = rep[0], ""
			else:
				orig, new = rep
			line = line.replace(orig, new)
		fn.write(line)
	f.close()
	fn.close()
			
			
def extractsub(path, options):
	dir, file = split(path)
	log.info("** Processing: %s **" % file)
	exe = join(options.mkvtoolnix,"mkvinfo.exe")
	chdir(dir)
	output = runcommand('"%s" "%s"' % (exe,file), True)
	
	subs, fileinfo = _getsublist(output)
	outnames = []
	for track in subs:
		log.info("** Extracting track: %s Default: %s **" % (track.num, track.default))
		outnames.append('%s:"%s.%s%s%s"' % (track.num, splitext(file)[0], track.num, ".default" if track.default else "", track.ext))
	
	exe = join(options.mkvtoolnix,"mkvextract.exe")
	runcommand('"%s" tracks "%s" %s' % (exe,file, " ".join(outnames)))
		
	tempfiles = []
	if options.file:
		r = codopen(options.file,"r","utf-8")
		reps = []
		for x in r:
			reps.append(x.strip().split('\t'))
		r.close()
		muxoptions = []
		for track in subs:
			if track.ext != "." and track.ext != "":
				oldfile = "%s.%s%s%s" % (splitext(file)[0], track.num, ".default" if track.default else "", track.ext)
				newfile = "%s.%s%s%s" % (splitext(file)[0], track.num, ".default" if track.default else "", "_replaced" + track.ext)
				move(oldfile, oldfile + "_old")
				oldfile = oldfile+"_old"
				tempfiles.append(oldfile)
				tempfiles.append(newfile)
				replacesubtext(oldfile, newfile, reps)
				#TrackThings.subtemplate
				# {lang}{trackname}{default}{fname}
				if options.default is None:
					muxoptions.append(TrackThings.subtemplate.format(lang=track.lang, trackname=track.name, default="yes" if track.default else "no", fname=newfile))
				else:
					if track.num == options.default:
						muxoptions.append(TrackThings.subtemplate.format(lang=track.lang, trackname=track.name, default="yes", fname=newfile))
					else:
						muxoptions.append(TrackThings.subtemplate.format(lang=track.lang, trackname=track.name, default="no", fname=newfile))
				
				
		# if remux do things here
		if options.remux:
			#--segment-uid
			exe = join(options.mkvtoolnix,"mkvmerge.exe")
			#make backup folder
			if exists("backups"):
				if not isdir("backups"):
					log.critical('"backups" is not a dir, bailing')
					exit(1)
			else: mkdir("backups")
			fn, ext = splitext(file)
			newfname = "%s%s%s" % (fn, options.suffix, ext)
			if options.removecrc:
				newfname = TrackThings.regexCRC.sub("", newfname)
			oldfname = "%s-old%s" % (fn, ext)
			oldfname = join(dir, "backups", oldfname)
			move(path, oldfname)
			command = '{cmd} -o "{fname}" {oldsubs} "{oldfname}" {subs}'
			log.info("** REMUXING FILE **")
			runcommand(command.format(cmd=exe, fname=file, oldsubs="-S" if not options.keeporig else "", oldfname=oldfname, subs=" ".join(muxoptions)))
			#also put subfiles into backup
			for z in tempfiles:
				move(join(dir,z), join(dir,"backups",z))
			if not options.noclean:
				try: rmtree("backups")
				except WindowsError:
					try: rmtree("backups")
					except WindowsError as e:
						log.error("%s" % str(e))

defaults = {
	"file" : None,
	"mkvtoolnix" : None,
	"remux" : False,
	"nobackup" : False,
	"default" : None,
	"keeporig" : False,
	"suffix" : "",
	"removecrc" : False,
	"noclean" : False,
	"debug" : False,
}

parser = OptionParser(usage="usage: %prog [options] [file[s]/dir[s]]")
parser.add_option("-f", "--file", dest="file", default=None,
	help="File to take replacements from", metavar="FILE")
parser.add_option("-m", "--mkvtoolnix", dest="mkvtoolnix", default=None,
	help="Location of MKVtoolnix files, i.e. folder with mkvinfo.exe in it", metavar="DIR")
parser.add_option("--no-config", dest="noconf", action="store_true", default=None,
	help='Do not attempt to read config file. Default is to always check for config.')
parser.add_option("-c", "--config", dest="conf", default=None, metavar="CONFIGFILE",
	help='Read from CONFIGFILE otherwise [scriptname].conf in script location.')
parser.add_option("-r", "--remux", action="store_true", dest="remux", default=None,
	help="Remux replaced subs into new file(s). Default is not to do this. (Use -n to not keep backups of original files)")
parser.add_option("-n", "--nobackup", action="store_true", dest="nobackup", default=None,
	help="Don't backup original files. Only useful when used with -r. Default is to keep backups.")
parser.add_option("-d", "--default", dest="default", metavar="TRACKNUM", default=None,
	help="Changes the default track to the tracknumber specified. Only useful when remuxing with -r. If not specified, when remuxing the default is to use the replaced default track.")
parser.add_option("-k", "--keeporig", action="store_true", dest="keeporig", default=None,
	help="Keeps the original subtitle tracks in the remuxed file, therefore only useful when remuxing with -r/--remux. Otherwise only the replaced subtracks will be remuxed.")
parser.add_option("-p", "--suffix", dest="suffix", metavar="SUFFIX", default=None,
	help="Adds SUFFIX to the remuxed file. Hence only applied when using -r/--remux")
parser.add_option("--removecrc", action="store_true", dest="removecrc", default=None,
	help="Removes CRC's from remuxed filenames. Hence only applied when using -r/--remux. WARNING: Has the potential to severely mangle filenames. Regex used: [^a-zA-Z0-9][a-fA-F0-9]{8}[^a-zA-Z0-9]")
parser.add_option("--noclean", action="store_true", dest="noclean", default=None,
	help="If remuxing, don't clean up temporary extracted subfiles. Default is to remove temp files when remuxing.")
parser.add_option("--debug", action="store_true", dest="debug", default=None,
	help="Print debug stuff")
	
(options, args) = parser.parse_args()

combine_options_fromfile(defaults, options, "subextractreplace.conf", __file__)

if options.debug:
	log.level=DEBUG
	for x in options.__dict__:
		log.debug("%s = %s" % (x, options.__dict__[x]))
		
if (not options.mkvtoolnix) or (not exists(join(options.mkvtoolnix,"mkvinfo.exe"))) or (not exists(join(options.mkvtoolnix,"mkvextract.exe")))\
	or (not exists(join(options.mkvtoolnix,"mkvmerge.exe"))):
	log.error("MKVtoolnix files not found. -h for help")
	exit(1)

if options.file:
	if isabs(options.file):
		if not exists(options.file):
			log.error("Replacement file (%s) not found." % options.file)
			exit(1)
	else:
		if exists(join(getcwd(),options.file)):
			options.file = join(getcwd(),options.file)
		else:
			log.error("Replacement file (%s) not found." % join(getcwd(),options.file))
			exit(1)		

paths = buildpathlist(args)

for path in paths:
	if isdir(path):
		for root, dirs, files in walk(path):
			for file in files:
				if splitext(file)[1] == ".mkv":
					extractsub(join(root,file),options)
	else:
		if splitext(path)[1] == ".mkv":
			extractsub(path,options)