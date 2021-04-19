from csv import reader, writer
from os import listdir
from os.path import join
from sys import argv, exit

if not len(argv) == 2:
	print("Require path.")
	exit(1)
IDIR = argv[1]
FILES = listdir(IDIR)

MONTHS = []
NUMBERMAP = {
	"1800" : 0,
	"13" : 0,
	"04" : 0,
	"INTERNATIONAL" : 0,
	"NATIONAL" : 0,
	"LOCAL" : 0,
}
for x in range(len(FILES)): MONTHS.append(dict(NUMBERMAP))

COSTS = {
	"1800": 25.0,
	"13" : 25.0,
	"04" : 12.0/60,
	"INTERNATIONAL" : 4.0/60,
	"NATIONAL" : 4.0/60,
	"LOCAL" : 4.0/60,
}

locs = set()
# Record Type,Account Number,Department Description,Service Number,Service Type,Usage Type Description,Date,Time,Rate,Duration,Destination,Destination Location,Charge(ex GST),GST Rate,Origin,Raw Units,Raw Units Type,Secondary Rated Amount,Charge ID
#     0            1                2                     3            4                 5               6    7    8    9          10              11               12            13       14     15         16             17                    18
MONTH = 0
for file in listdir(IDIR):
	fn = join(IDIR, file)
	if "rec002" not in file: continue
	print(("Processing %s..." % fn))
	with open(fn, 'r') as csvfile:
		creader = reader(csvfile)
		first = True
		for row in creader:
			if first:
				first = False
				continue
			if row[5] == "International":
				MONTHS[MONTH]["INTERNATIONAL"] += int(row[15])
				locs.add(row[11])
			else:
				for key in NUMBERMAP:
					if row[10].startswith(key):
						if row[10].startswith("04"):
							if int(row[15]) < 7000:
								MONTHS[MONTH][key] += int(row[15])
						else:
							MONTHS[MONTH][key] += 1
						break
				else:
					if row[10].startswith("03"):
						MONTHS[MONTH]["LOCAL"] += int(row[15])
					elif row[10].startswith("0"):
						if int(row[15]) < 7000:
							MONTHS[MONTH]["NATIONAL"] += int(row[15])
					else:
						print(("UNEXPECTED NUMBER: %s" % row[10]))
	MONTH += 1

TOTAL = 0

with open('breakdown.csv', 'w') as csvfile:
	csvout = writer(csvfile)
	csvout.writerow(["Month"] + list(NUMBERMAP.keys()))
	i = 0
	for map in MONTHS:
		csvout.writerow([i] + [(map[x]*COSTS[x]/100) for x in NUMBERMAP])
		for x in NUMBERMAP:
			NUMBERMAP[x] += map[x]
		i += 1


for key in NUMBERMAP:
	print(("%s: %s \t\t\t($%s)" % (key, NUMBERMAP[key], (NUMBERMAP[key]*COSTS[key])/100)))
	TOTAL += (NUMBERMAP[key]*COSTS[key])
print(locs)

print(("Total: %s" % (TOTAL/100)))


#~ 13: 117                         ($25.74)
#~ 04: 37656                       ($81.588)
#~ 1800: 22                        ($0)
#~ INTERNATIONAL: 12373    ($8.24866666667)
#~ NATIONAL: 767           ($76.7)
#~ set(['UK', 'USA', 'Hawaii'])
#~ Total: 192.276666667
