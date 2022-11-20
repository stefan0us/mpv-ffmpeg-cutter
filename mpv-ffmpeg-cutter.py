import argparse
import heapq
import os
import random
import subprocess

SCREENSHOT_DIR_NAME = 'screenshot'
SLICE_DIR_NAME = 'slice'
MPV_PRESET_OPTIONS = {
    '--keep-open': 'yes'
}
FFMPEG_PRESET_OPTIONS = {
    '-c:v': 'libx265',
    '-c:a': 'copy',
    '-x265-params': 'crf=25'
}


def option_dict_to_str(option_dict, preset_option_dict=None, connect_symbol=' '):
    effective_option_dict = option_dict if not preset_option_dict else preset_option_dict | option_dict
    return ' '.join([f"{k}{connect_symbol}{v}" for k, v in effective_option_dict.items()])


def create_file_timestamp_map(workdir: str):
    screenshot_dir = os.path.join(workdir, SCREENSHOT_DIR_NAME)
    screenshot_files = os.listdir(screenshot_dir)
    random.shuffle(screenshot_files)
    file_timestamp_list_map = {}
    for file_path in screenshot_files:
        ext_idx = file_path.rfind('.')
        ts_idx = file_path.rfind('_')
        name, ts = file_path[:ts_idx], file_path[ts_idx + 1:ext_idx]
        heapq.heappush(file_timestamp_list_map.setdefault(name, []), float(ts))
    return file_timestamp_list_map


def start_all_cut(workdir: str, file_timestamp_map: dict, skip: bool):
    slice_dir = os.path.join(workdir, SLICE_DIR_NAME)
    if not os.path.exists(slice_dir):
        os.mkdir(slice_dir)
    for file_path, ts_list in file_timestamp_map.items():
        video_name, video_ext = os.path.splitext(file_path)
        video_path = os.path.join(workdir, file_path)
        ts_length = len(ts_list)
        for idx in range(ts_length // 2):
            slice_path = os.path.join(slice_dir, f'{video_name}_{idx+1}{video_ext}')
            start_time = heapq.heappop(ts_list)
            end_time = heapq.heappop(ts_list)
            if os.path.exists(slice_path):
                continue
            ffmpeg_option_str = option_dict_to_str(
                {
                    '-ss': start_time,
                    '-to': end_time
                },
                FFMPEG_PRESET_OPTIONS,
                connect_symbol=' '
            )
            ffmpeg_cmd = f'ffmpeg -i "{video_path}" {ffmpeg_option_str} "{slice_path}"'
            print(ffmpeg_cmd)
            if not skip:
                input('continue to transcode.')
            with subprocess.Popen(ffmpeg_cmd, shell=True, stdout=subprocess.PIPE) as p:
                for line in p.stdout:
                    print(line, end='')
            if p.wait() != 0:
                raise subprocess.CalledProcessError(p.returncode, ffmpeg_cmd)


def spawn_mpv_window(workdir, input_file_path):
    mpv_option_str = option_dict_to_str(
        {
            '--screenshot-template': f"\"{os.path.join(workdir, SCREENSHOT_DIR_NAME, r'%f_%wf')}\""
        },
        preset_option_dict=MPV_PRESET_OPTIONS,
        connect_symbol='='
    )
    mpv_cmd = f'mpv {mpv_option_str} "{input_file_path}"'
    print(mpv_cmd)
    subprocess.check_call(mpv_cmd, shell=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--workdir', help='working directory.', type=str)
    parser.add_argument('-i', '--input-file', help='video file to play and cut.', type=str)
    parser.add_argument('-s', '--skip', help='skip all confirmations.',
                        action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()
    input_file_path, input_workdir, skip = args.input_file, args.workdir, args.skip
    if input_workdir:
        if not os.path.isdir(input_workdir):
            raise Exception('input workdir is not a directory.')
        workdir = input_workdir
    else:
        if not input_file_path:
            raise Exception('input file or workdir not specified.')
        workdir = os.path.dirname(input_file_path)
    if input_file_path:
        if not os.path.isfile(input_file_path):
            raise Exception('intput file is not a file.')
        spawn_mpv_window(workdir, input_file_path)
    if not skip:
        input('continue to process.')
    file_timestamp_map = create_file_timestamp_map(workdir)
    start_all_cut(workdir, file_timestamp_map, skip)


if __name__ == '__main__':
    main()
