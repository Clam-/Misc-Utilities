LoadPlugin("C:\Stuff\Video\ffms2-2.40-msvc\x64\ffms2.dll")
VID = "{VID}"
IMG = "{IMG}"

FFIndex(VID)
video = AudioDub( FFVideoSource(VID), FFAudioSource(VID)).ConvertToYV24()
video = video.Trim({START}, {END} )

still = AudioDub(ImageSource(IMG, fps=30, end=90), BlankClip(length=90,fps=30,channels=video.AudioChannels,audio_rate=video.AudioRate)).ConvertToYV24()

Dissolve(still, video, 15).ConvertToYV12()
