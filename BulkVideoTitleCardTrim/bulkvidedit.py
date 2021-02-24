from subprocess import run
from csv import DictReader
from sys import argv, exit

if len(argv) != 2:
    print("Need filename of edits.csv")
    exit(1)

def timecode(s, fps):
    if not s: return 0
    hh,mm,ss = (int(x) for x in s.split(":"))
    frames = hh*fps*60*60
    frames += mm*fps*60
    frames += ss*fps
    return frames

FPS=30
INPUT_DIR="INPUT/%s"
IMG_DIR="IMG/%s"
OUTPUT_DIR="OUTPUT/%s"
AVS_TEMPLATE="script.avs"
FFMPEG="c:/Stuff/Tools/ffmpeg-N-101191-g51a9f487ae-win64-gpl/bin/ffmpeg"
#0 is img, 1 is vid, 2 is start, 3 is end, 4 is output
CMD_TMPL='"%s" -i temp.avs -c:v libx264 -preset slower -profile:v high -crf 16 -c:a aac -b:a 128k "{0}"' % FFMPEG

with open(argv[1], encoding='utf-8-sig') as csvfile:
    reader = DictReader(csvfile)
    for row in reader:
        img = "{0}.png".format(IMG_DIR % row["Video Name"])
        vid = "{0}.mp4".format(INPUT_DIR % row["Video Name"])
        out = "{0}.mp4".format(OUTPUT_DIR % row["Video Name"])
        start=row["Start cut point (HH:MM:SS)"]
        end=row["End cut point (HH:MM:SS)"]

        # create script
        with open(AVS_TEMPLATE) as avsf:
            with open("temp.avs", "w") as avso:
                avso.write(avsf.read().format(IMG=img, VID=vid,START=timecode(start,FPS),END=timecode(end,FPS)))
        cmd = CMD_TMPL.format(out)
        print(repr(cmd))
        run(cmd, shell=True)
