import sys
import unicodecsv as csv
import json

if len(sys.argv) != 2:
    print "Need log file"
    sys.exit(1)

COLTITLES = {}
COLNUMBER = 0

infilename = sys.argv[1]
reader = csv.reader(open(infilename,'rb'), dialect='excel', encoding='utf-8')
writer = csv.writer(open(infilename+"-output.csv","wb"), dialect='excel', encoding='utf-8')
firstrow = True
for row in reader:
    if firstrow:
        for counter,field in enumerate(row):
            COLTITLES[field] = counter
            COLNUMBER += 1
        firstrow = False
        continue
    # row 9 JSON
    wrow = row[:9] + [""]*100
    d = json.loads(row[9])
    for key in d:
        if key not in COLTITLES:
            COLTITLES[key] = COLNUMBER
            COLNUMBER += 1
        if key in COLTITLES:
            wrow[COLTITLES[key]] = d[key]

    writer.writerow(wrow)
writer.writerow(sorted(COLTITLES, key=lambda k: COLTITLES[k]))
