# mpv-ffmpeg-cutter

A simple script to create a pipeline of video cutting with mpv and ffmpeg.

```
usage: mpv-ffmpeg-cutter.py [-h] [-i INPUT_FILE] [-m | --spawn-mpv-window | --no-spawn-mpv-window] [-t | --iterate | --no-iterate] [-s | --skip | --no-skip]

options:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input-file INPUT_FILE
                        video file to play and cut.
  -m, --spawn-mpv-window, --no-spawn-mpv-window
                        require to spawn mpv window and take screenshot.
  -t, --iterate, --no-iterate
                        iterate all files after input file sequentially.
  -s, --skip, --no-skip
                        skip all confirmations.
```
