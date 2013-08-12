#subextractreplace v0.9

#run python subextractreplace -h for helps

#requires util.py >=0.3

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
	from util import buildpathlist, version
	if version < 0.3: 
		print "util version too low. Need 0.3 or greater."
		exit(1)
except:
	print "util.py missing or version too low. Need 0.3 or greater."
	exit(1)
	

from os.path import isdir, exists, join, splitext, isabs, split
from os import getcwdu, walk, chdir, mkdir
from shutil import rmtree, move
from subprocess import Popen, PIPE, STDOUT
from cStringIO import StringIO
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
				track.num = m.group(1)-1
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
	exe = join(options.mkvtools,"mkvinfo.exe")
	chdir(dir)
	output = runcommand('"%s" "%s"' % (exe,file), True)
	
	subs, fileinfo = _getsublist(output)
	outnames = []
	for track in subs:
		log.info("** Extracting track: %s Default: %s **" % (track.num, track.default))
		outnames.append('%s:"%s.%s%s%s"' % (track.num, splitext(file)[0], track.num, ".default" if track.default else "", track.ext))
	
	exe = join(options.mkvtools,"mkvextract.exe")
	runcommand('"%s" tracks "%s" %s' % (exe,file, " ".join(outnames)))
		
	tempfiles = []
	if options.filename:
		r = codopen(options.filename,"r","utf-8")
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
				if not options.default:
					muxoptions.append(TrackThings.subtemplate.format(lang=track.lang, trackname=track.name, default="yes" if track.default else "no", fname=newfile))
				else:
					if track.num == options.default:
						muxoptions.append(TrackThings.subtemplate.format(lang=track.lang, trackname=track.name, default="yes", fname=newfile))
					else:
						muxoptions.append(TrackThings.subtemplate.format(lang=track.lang, trackname=track.name, default="no", fname=newfile))
				
				
		# if remux do things here
		if options.remux:
			#--segment-uid
			exe = join(options.mkvtools,"mkvmerge.exe")
			#make backup folder
			if exists("backups"):
				if not isdir("backups"):
					log.critical('"backups" is not a dir, bailing')
					exit(1)
			else: mkdir("backups")
			fn, ext = splitext(file)
			oldfname = "%s-old%s" % (fn, ext)
			oldfname = join(dir, "backups", oldfname)
			move(path, oldfname)
			command = '{cmd} -o "{fname}" {oldsubs} "{oldfname}" {subs}'
			log.info("** REMUXING FILE **")
			runcommand(command.format(cmd=exe, fname=file, oldsubs="-S" if not options.keep else "", oldfname=oldfname, subs=" ".join(muxoptions)))
			#also put subfiles into backup
			for z in tempfiles:
				move(join(dir,z), join(dir,"backups",z))
			if not options.noclean:
				rmtree("backups")


parser = OptionParser(usage="usage: %prog [options] [file[s]/dir[s]]")
parser.add_option("-f", "--file", dest="filename", default=None,
	help="File to take replacements from", metavar="FILE")
parser.add_option("-m", "--mkvtoolnix", dest="mkvtools", default=None,
	help="Location of MKVtoolnix files, i.e. folder with mkvinfo.exe in it", metavar="DIR")
parser.add_option("-r", "--remux", action="store_true", dest="remux", default=False,
	help="Remux replaced subs into new file(s). Default is not to do this. (Use -n to not keep backups of original files)")
parser.add_option("-n", "--nobackup", action="store_true", dest="nobackup", default=False,
	help="Don't backup original files. Only useful when used with -r. Default is to keep backups.")
parser.add_option("-d", "--default", dest="default", metavar="TRACKNUM",
	help="Changes the default track to the tracknumber specified. Only useful when remuxing with -r. If not specified, when remuxing the default is to use the replaced default track.")
parser.add_option("-k", "--keeporig", action="store_true", dest="keep", default=False,
	help="Keeps the original subtitle tracks in the remuxed file, therefore only useful when remuxing with -r. Otherwise only the replaced subtracks will be remuxed.")
parser.add_option("--noclean", action="store_true", dest="noclean", default=False,
	help="If remuxing, don't clean up temporary extracted subfiles. Default is to remove temp files when remuxing.")
parser.add_option("--debug", action="store_true", dest="debug", default=False,
	help="Print debug stuff")
	
(options, args) = parser.parse_args()

if options.debug:
	log.level=DEBUG
if (not options.mkvtools) or (not exists(join(options.mkvtools,"mkvinfo.exe"))) or (not exists(join(options.mkvtools,"mkvextract.exe")))\
	or (not exists(join(options.mkvtools,"mkvmerge.exe"))):
	log.error("MKVtoolnix files not found. -h for help")
	exit(1)

if options.filename:
	if isabs(options.filename):
		if not exists(options.filename):
			log.error("Replacement file not found.")
			exit(1)
	else:
		if exists(join(getcwdu(),options.filename)):
			options.filename = join(getcwdu(),options.filename)
		else:
			log.error("Replacement file not found.")
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