import argparse
import heapq
import os
import random
import subprocess
from multiprocessing.pool import ThreadPool
from pathlib import Path

SCREENSHOT_DIR_NAME = 'screenshot'
SLICE_DIR_NAME = 'slice'
MPV_PRESET_OPTIONS = {
    '--keep-open': 'yes'
}
FFMPEG_PRESET_OPTIONS = {
    '-c:v': 'hevc_nvenc',
    '-filter:a': 'loudnorm',
    '-x265-params': 'crf=8',
    '-b:v': '10M'
}
PROCESS_POOL_SIZE = 2


def option_dict_to_str(option_dict, preset_option_dict=None, connect_symbol=' '):
    effective_option_dict = option_dict if not preset_option_dict else preset_option_dict | option_dict
    return ' '.join([f"{k}{connect_symbol}{v}" for k, v in effective_option_dict.items()])


def create_file_timestamp_map(workdir: str, file_path: str):
    screenshot_dir = os.path.join(workdir, SCREENSHOT_DIR_NAME)
    screenshot_files = [f for f in os.listdir(screenshot_dir) if os.path.basename(file_path) in f]
    random.shuffle(screenshot_files)
    file_timestamp_list_map = {}
    for file_path in screenshot_files:
        ext_idx = file_path.rfind('.')
        ts_idx = file_path.rfind('_')
        name, ts = file_path[:ts_idx], file_path[ts_idx + 1:ext_idx]
        heapq.heappush(file_timestamp_list_map.setdefault(name, []), float(ts))
    return file_timestamp_list_map


def submit_transcode_task(workdir: str, file_timestamp_map: dict, thread_pool: ThreadPool, skip: bool):
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
            thread_pool.apply_async(run_ffmpeg_process, (ffmpeg_cmd,))


def run_ffmpeg_process(ffmpeg_cmd):
    with subprocess.Popen(ffmpeg_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as p:
        p.communicate()
    if p.wait() != 0:
        raise subprocess.CalledProcessError(p.returncode, ffmpeg_cmd)


def run_mpv_process(workdir, input_file_path):
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


def gen_mpv_input_file_list(workdir: str, input_file: str, sequential: bool):
    if not sequential:
        return [input_file]
    sort_key_func = os.path.getctime
    input_file_sort_key = sort_key_func(input_file)
    return sorted([file_path.as_posix() for file_path in Path(workdir).iterdir()
                   if os.path.isfile(file_path)
                   and os.path.splitext(file_path)[1] in ('.mp4')
                   and sort_key_func(file_path.as_posix()) > input_file_sort_key],
                  key=sort_key_func)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input-file', help='video file to play and cut.', type=str)
    parser.add_argument('-m', '--spawn-mpv-window', help='require to spawn mpv window and take screenshot.',
                        action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-t', '--iterate', help='iterate all files after input file sequentially.',
                        action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-s', '--skip', help='skip all confirmations.',
                        action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()
    file_path, spawn_mpv_window, skip, iterate = args.input_file, args.spawn_mpv_window, args.skip, args.iterate
    workdir = os.path.dirname(file_path)
    if file_path:
        if not os.path.isfile(file_path):
            raise Exception('intput file is not a file.')
    process_thread_pool = ThreadPool(PROCESS_POOL_SIZE)
    for file in gen_mpv_input_file_list(workdir, file_path, iterate):
        if spawn_mpv_window:
            run_mpv_process(workdir, file)
        file_timestamp_map = create_file_timestamp_map(workdir, file)
        submit_transcode_task(workdir, file_timestamp_map, process_thread_pool, skip)
    process_thread_pool.close()
    process_thread_pool.join()


if __name__ == '__main__':
    main()
