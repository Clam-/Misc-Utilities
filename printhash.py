from sys import argv, exit
from zlib import crc32
from hashlib import md5


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
			
			
			
def getsum(path,method):
	f = open(path,"rb")
	#lol arbitrary 10MB
	h = Hash(f.read(10485760), method)
	chunk = f.read(10485760)
	while chunk:
		h.update(chunk)
		chunk = f.read(10485760)
	f.close()
	return h.gibehex()
	
	
if len(argv) != 3:
	print("Need filename and hash method [crc,md5]")
	exit(1)
	
print(getsum(argv[1], argv[2]))