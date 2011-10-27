#whatever 2 UTF8

from sys import argv, exit
from codecs import open as codopen, BOM_UTF8
from os.path import splitext

if len(argv) < 2 or len(argv) > 4: 
	print "Need stuff: filename ['BOM'] [encoding]  Where encoding can be anything from http://docs.python.org/library/codecs.html#standard-encodings", argv
	exit(1)
	
fname = argv[1]
enc = "sjis"
bom = False
if len(argv) == 3:
	if argv[2] == "BOM":
		bom = True
	else:
		enc = argv[2]
if len(argv) == 4:
	if argv[2] == "BOM":
		bom = True
	enc = argv[3]
sfname = splitext(fname)

if bom:
	#put BOM mark 'cause foobar is lame
	fw = open(sfname[0]+"-utf8"+sfname[1],"w")
	fw.write(BOM_UTF8)
	fw.close()

fr = codopen(fname,"r",enc)
fw = None
if not bom:
	fw = codopen(sfname[0]+"-utf8"+sfname[1],"w","utf-8")
else:
	fw = codopen(sfname[0]+"-utf8"+sfname[1],"a","utf-8")
fw.write(fr.read())
fw.close()
fr.close()