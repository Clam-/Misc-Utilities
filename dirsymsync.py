# dirsymsync - https://github.com/Clam-/Misc-Utilities
#
# Admins need to be in group "admin"
# Users need to be in group "users"
#
# This script needs to be run with a new user that is in both "admin" and "users"
# "source" needs to have chmod g+s, and group "users"
# "storage" needs to have chmod g+s and group "admin"

# if using lftp you need to use the -p flag when mirror'ing (-R to upload)
# See wiki for more infos I guess

from pyinotify import ProcessEvent, WatchManager, Notifier,\
	IN_CLOSE_WRITE, IN_MOVED_TO, IN_DELETE, IN_CREATE, IN_ATTRIB

from os import chmod, getuid, listdir, mkdir, makedirs, symlink, unlink, lstat, rename, umask
from os.path import dirname, exists, isdir, isfile, islink, lexists, join, realpath, relpath
from shutil import copy, rmtree
from pwd import getpwuid
from grp import getgrgid
from stat import S_ISLNK, S_ISDIR, S_ISREG, S_ISGID, S_IRWXG, S_IRGRP, S_IWGRP, ST_MODE, ST_GID, ST_UID
from sys import exc_info
from traceback import format_exception_only
from datetime import datetime
from optparse import OptionParser
from sys import exit

#important if you aren't running from a shell running with umask 0002 already
umask(0002)
#alternativly I could chmod everything after creation but that is kind of tedious.

from emailmodule import Mailer

from logging import basicConfig, getLogger, INFO
basicConfig(level=INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y%m%d %H:%M:%S")
log = getLogger("dirsymsync")


class PermissionModError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)


#options
parser = OptionParser(usage="usage: %prog [options] source storage",
	description='%prog will replace files added to "source" with symlinks and store the\
actual files in "storage." The order of these arguments is important.')
parser.add_option("-p", "--perms", dest="perms", type="int", metavar="OCTAL",
	help='Permission on "storage" directories. (Use 0 prefix, 2 for setgid) [02771]')
parser.add_option("--mail", dest="mail", action="store_true",
	help='Enable mailing of errors. [False]')
parser.add_option("--mail-to", dest="mailto", metavar="EMAILADDR",
	help='Address to send mail to.')
parser.add_option("--mail-from", dest="mailfrom", metavar="EMAILADDR",
	help='Address to send mail from.')
parser.add_option("--mail-subject", dest="mailsubject", metavar="SUBJET",
	help='Subject of error mail. (Prepended with module name and date)')
parser.add_option("--no-setgidwarn", dest="setgidwarn", action="store_false",
	help='Turns off warning about setgidbit not set. [Not set]')
parser.add_option("--groupsource", dest="groupsource", metavar="GROUP",
	help='Group name to check for when checking permissions on "source".')
parser.add_option("--groupstorage", dest="groupstorage", metavar="GROUP",
	help='Group name to check for when checking permissions on "storage".')
parser.add_option("--nosync", dest="sync", action="store_false",
	help="Don't attempt to manually sync files at startup.")
parser.add_option("--nomonitor", dest="monitor", action="store_false",
	help="""Don't monitor "source" and "storage" directories for changes. (Only really useful if you are using --nosync)""")

parser.set_defaults(perms=02771, mail=False, mailto=None, mailfrom=None, subject="Error happen",
	setgidwarn=True, groupsource=None, groupstorage=None, sync=True, monitor=True)

(options, args) = parser.parse_args()
if len(args) < 2:
	print 'dirsymsync requires at least "source" and "storage" directories to be specified.  Provided: %s\nExiting.' % args
	exit(1)
options.source, options.storage = args[:2]
mailerargs = {"sourcename" : "dirsymsync"}
if options.mailto: mailerargs["toaddr"] = options.mailto
if options.mailfrom: mailerargs["fromaddr"] = options.mailfrom
if options.mailsubject: mailerargs["subject"] = options.mailsubject
options.user = getpwuid(getuid()).pw_name

mailer = None
if options.mail:
	mailer = Mailer(**mailerargs)

def symsyncsource(source, storage, options):
	#traverse the source dir and make sure links are real
	#permissions are valid and stuff.
	for entry in listdir(source):
		newsource = join(source, entry)
		newstorage = join(storage, entry)
		mode = lstat(newsource)[ST_MODE]
		if S_ISLNK(mode):
			if isdir(realpath(newsource)): unlink(newsource)
			elif exists(newsource): continue
			else: unlink(newsource)
		elif S_ISDIR(mode):
			#check permissions
			checkperms(newsource, options)
			#check if in storage, add if not
			if not exists(newstorage): 
				mkdir(newstorage)
				chmod(newstorage, options.perms)
			#recurse
			symsyncsource(newsource, newstorage, options)
			
		elif S_ISREG(mode):
			#check permissions
			checkperms(newsource, options)
			#check if already in storage
			if not exists(newstorage): 
				checkremlink(newstorage)
				copy(newsource, newstorage)
			#unlink
			unlinked = False
			try:
				unlink(newsource)
				unlinked = True
			except OSError:
				log.warn("Unable to remove file in source: %s" % newsource)
			#create symlink
			if unlinked:
				makerelsymlink(newstorage, newsource)
				
def symsyncstorage(source, storage, options):
	#traverse the storage dir and make sure there is a symlink
	#for every file and the dirstructure is proper
	for entry in listdir(storage):
		newsource = join(source, entry)
		newstorage = join(storage, entry)
		mode = lstat(newstorage)[ST_MODE]
		#There shouldn't really be any links in storage, but whatever, just ignore for now
		if S_ISDIR(mode):
			#check permissions
			checkperms(newstorage, options, storage=True)
			#check to see if dir exists on source side
			if exists(newsource):
				#if anything else, let's get rid of it, storage has authority
				if not isdir(newsource):
					unlink(newsource)
					mkdir(newsource)
			else:
				mkdir(newsource)
			#recurse
			symsyncstorage(newsource, newstorage, options)
		elif S_ISREG(mode):
			#check perms
			checkperms(newstorage, options, storage=True)
			#make sure there's a symlink on the other side
			if exists(newsource):
				#again, storage is authority
				if not islink(newsource):
					unlink(newsource)
					makerelsymlink(newstorage, newsource)
			else:
				makerelsymlink(newstorage, newsource)
			

def checkperms(path, options, storage=False):
	#make sure group is thing, too
	perm = options.perms
	st = lstat(path)
	mode = st[ST_MODE]
	if S_ISDIR(mode): 
		if not ((mode & S_ISGID) == S_ISGID) and options.setgidwarn: log.warn("setgid not set on: %s" % path)
		if storage:
			if not ((mode & perm) == perm): 
				#attempt fix
				try: chmod(path, perms)
				except OSError: log.warn("Unable to apply permission fix (%s) on %s" % (perm, path))
		if not ((mode & S_IRWXG) == S_IRWXG):
			#attempt fix
			try: chmod(path, mode | S_IRWXG)
			except OSError: log.warn("Directory doesn't have group read/write/exec: %s" % path)
	elif S_ISREG(mode):
		tmask = S_IRGRP & S_IWGRP
		if not ((mode & tmask) == tmask):
			#attempt fix
			try: chmod(path, mode | tmask)
			except OSError: log.warn("File doesn't have group read/write: %s" % path)
	if storage and options.groupstorage:
		#check group
		name = getgrgid(st[ST_GID]).gr_name
		if name != options.groupstorage: 
			log.warn('[STOR] Group owner (%s) is not "%s"' % (name, options.groupstorage))
	elif (not storage) and options.groupsource:
		#check group
		name = getgrgid(st[ST_GID]).gr_name
		if name != options.groupsource:
			log.warn('[SRC] Group owner (%s) is not "%s"' % (name, options.groupsource))

def exceptionwrapper(func):
	def fn(*args, **kwargs):
		try:
			func(*args, **kwargs)
		except Exception:
			log.exception("EXCEPTION:")
			if options.mail:
				mailer.addmessage("%s - %s" % (datetime.now(), format_exception_only(*exc_info()[:2])[0]))
	return fn

def oppositerelpath(fullpath, source, dest):
	return join(dest, relpath(fullpath, source))

def checkowner(path, username):
	return getpwuid(lstat(path)[ST_UID]).pw_name == username

def makerelsymlink(source, dest):
	destdir = dirname(dest)
	if not exists(destdir): makedirs(destdir)
	symlink(relpath(source, destdir), dest)
	
def checkremlink(path, warn=True):
	if lexists(path): 
		if warn: log.warn("Broken symlink removed: %s -> %s" % (path, realpath(path)))
		unlink(path)

def makedir(path, perms=None):
	if not exists(path):
		checkremlink(path)
		mkdir(path)
		if perms:
			chmod(path, perms)

class DummyHandler(ProcessEvent):
	pass

class SourceHandler(ProcessEvent):
	def my_init(self, options):
		self.options = options
	
	@exceptionwrapper
	def process_IN_CREATE(self, event):
		if event.dir:
			if checkowner(event.pathname, self.options.user): return
			#check if doesn't exists in storage
			log.debug("[SRC] New path: %s" % event.pathname)
			npath = oppositerelpath(event.pathname, self.options.source, self.options.storage)
			if not exists(npath):
				checkremlink(npath)
				#create
				log.debug("[SRC] Creating: %s" % npath)
				makedir(npath, self.options.perms)
	
	@exceptionwrapper
	def process_IN_DELETE(self, event):
		if not event.name: return
		#if checkowner(event.pathname): return
		log.debug("[SRC] Path deleted: %s" % event.pathname)
		npath = oppositerelpath(event.pathname, self.options.source, self.options.storage)
		if not exists(npath): 
			checkremlink(npath)
			return
		if event.dir:
			#recreate dir structure? Maybe just remake dir is enough
			log.debug("[SRC] Remaking dir: %s" % event.pathname)
			makedir(event.pathname)
		else:
			#recreate symlink
			log.debug("[SRC] Remaking symlink: %s -> %s" % (event.pathname, npath) )
			makerelsymlink(npath, event.pathname)
		
	@exceptionwrapper
	def process_IN_CLOSE_WRITE(self, event):
		#copy then delete and create symlink
		if not event.dir:
			if checkowner(event.pathname, self.options.user): return
			log.debug("[SRC] File uploaded and closed: %s" % event.pathname)
			storfile = oppositerelpath(event.pathname, self.options.source, self.options.storage)
			log.debug("[SRC] Copying %s -> %s" % (event.pathname, storfile) )
			copy(event.pathname, storfile)
			log.debug("[SRC] Removing %s" % event.pathname)
			unlink(event.pathname)
			#lol the following will happen because WE deleted original file
			#~ log.info("[SRC] Symlinking: %s -> %s" % (event.pathname, storfile) )
			#~ symlink(storfile, event.pathname)
		
	#do this sometime
	@exceptionwrapper
	def process_IN_MOVED_TO(self, event):
		if checkowner(event.pathname, self.options.user): return
		log.debug("[SRC] Reverting move %s -> %s" % (event.pathname, event.src_pathname) )
		rename(event.pathname, event.src_pathname)
	
	@exceptionwrapper
	def process_IN_ATTRIB(self, event):
		if checkowner(event.pathname, self.options.user): return
		raise PermissionModError("Permission changed in: %s" % event.pathname)

class StorageHandler(ProcessEvent):
	def my_init(self, options):
		self.options = options
		
	@exceptionwrapper
	def process_IN_CREATE(self, event):
		npath = oppositerelpath(event.pathname, self.options.storage, self.options.source)
		if checkowner(event.pathname, self.options.user): return
		log.debug("[STOR] Created path: %s" % event.pathname)
		if event.dir:
			#create folder on other side
			if not exists(npath):
				checkremlink(npath)
				log.debug("[STOR] mkdir: %s" % npath)
				makedir(npath)
				#chmod(event.pathname, 0771)
		else:
			#create symlink
			if not exists(npath):
				checkremlink(npath)
				log.debug("[STOR] Symlinking: %s -> %s" % (event.pathname, npath))
				makerelsymlink(event.pathname, npath)
			else:
				if not checkowner(event.pathname, self.options.user):
					#remove if not admin owns (symlink will be recreated on this delete event)
					if lexists(npath):
						unlink(npath)
			
	@exceptionwrapper
	def process_IN_DELETE(self, event):
		#remove things in source
		if not event.name: return
		log.debug("[STOR] Path deleted: %s" % event.pathname)
		npath = oppositerelpath(event.pathname, self.options.storage, self.options.source)
		if lexists(npath):
			if event.dir:
				log.debug("[STOR] Nuking tree: %s" % npath)
				rmtree(npath)
			else:
				log.debug("[STOR] Unlinking: %s" % npath)
				unlink(npath)
		else:
			log.warn("""[STOR] Deleted item "%s" but SRC "%s" didn't exist""" % (event.pathname, npath))

	#do this sometime
	@exceptionwrapper
	def process_IN_MOVED_TO(self, event):
		if checkowner(event.pathname, self.options.user): return
		npath = oppositerelpath(event.pathname, self.options.storage, self.options.source)
		nsrc = oppositerelpath(event.src_pathname, self.options.storage, self.options.source)
		if event.dir:
			log.debug("[STOR] Moved STOR %s -> %s" % (event.src_pathname, event.pathname) )
			log.debug("[STOR] Moving SRC %s -> %s" % (npath, nsrc) )
			rename(npath, nsrc)
		else:
			#delete symlink and make new one since delete event won't remake since it doesn't exist anymore
			checkremlink(nsrc, warn=False)
			makerelsymlink(event.pathname, npath)
	
	@exceptionwrapper
	def process_IN_ATTRIB(self, event):
		if checkowner(event.pathname, self.options.user): return
		raise PermissionModError("Permission changed in: %s" % event.pathname)


log.info("Starting...")
if options.sync:
	log.info("Starting manual sync...")
	symsyncsource(options.source, options.storage, options)
	symsyncstorage(options.source, options.storage, options)
	log.info("Sync done.")
if not options.monitor: exit()
if options.mail:
	log.info("Starting mailer thread...")
	mailer.start()
log.info("Source: %s" % options.source)
log.info("Storage: %s" % options.storage)
log.info("Permissions: %o" % options.perms)
# Instanciate a new WatchManager (will be used to store watches).
wm = WatchManager()
# Associate this WatchManager with a Notifier (will be used to report and
# process events).

notifier = Notifier(wm, default_proc_fun=DummyHandler())
# Add a new watch on /tmp for ALL_EVENTS.
mask = IN_CLOSE_WRITE | IN_MOVED_TO | IN_DELETE | IN_CREATE | IN_ATTRIB
wm.add_watch(options.source, mask, rec=True, auto_add=True, proc_fun=SourceHandler(options=options))
wm.add_watch(options.storage, mask, rec=True, auto_add=True, proc_fun=StorageHandler(options=options))
# Loop forever and handle events.
log.info("Waiting for events...")
try: notifier.loop()
except Exception:
	log.exception("EXCEPTION:")
	mailer.addmessage("ALERT: PROGRAM CLOSING:\n%s - %s" % (datetime.now(), format_exception_only(*exc_info()[:2])))
if options.mail: mailer.quit()
