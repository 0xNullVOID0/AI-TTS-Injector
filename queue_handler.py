import io
import os
import queue
import threading
import requests
import sounddevice as sd
import soundfile as sf
import time

from config_handler import config
from profiler import profiler


class _QueueHandler():
    def __init__(self):
        self.audio_queue = queue.Queue(100)
        self.download_queue = queue.Queue(10)
        self.ocr_queue = queue.Queue(50)
        self.downloader = None
        self.audio_player = None
        self.ocr_worker = None
        self.audio_played_counter = 0
        self.request_counter = 0
        self.succ_request_counter = 0
        self.buffer = 0
        self.buffer_threshold = 5000 # ms
        self.tier = 0 # tier/stage?
        self.stage = 0

        # set global events for easy start/stop
        config.audio_stop_event = threading.Event()
        config.download_stop_event = threading.Event()

    def increaseBuffer(self):
        # TODO buffer only possible if same character keeps talking, the moment name switches u gotta stop and reset, due to different voices, or only do a voice difference check not even name
        return True

    # toggle all queues and worker threads
    def toggle(self):
        if config.running:
            print('Pausing/Stopping Queue worker')
            config.stop()
            config.audio_stop_event.set()
            config.download_stop_event.set()
            sd.stop()  # force audio stop
        else:
            print('Starting Queue worker')
            config.start()
            config.audio_stop_event.clear()
            config.download_stop_event.clear()

            # re set worker threads
            self.setDownloader()
            self.setAudioPlayer()

    def add(self, item, item_type):
        print(f"Adding {item_type} to queue: {item}")
        if item_type == 'audio':
            self.audio_queue.put(item)
            print(f"{item_type} queue size: {self.audio_queue.qsize()}")
        elif item_type == 'download':
            self.download_queue.put(item)
            print(f"{item_type} queue size: {self.download_queue.qsize()}")
        elif item_type == 'ocr':
            self.ocr_queue.put(item)
            print(f"{item_type} queue size: {self.ocr_queue.qsize()}")

    @profiler.time_profile
    def dl(self, download_task):
        try:
            self.request_counter += 1
            print(f"Request counter: {self.request_counter}")

            response = requests.post(download_task["url"], json=download_task["payload"], timeout=10)
            print(f"Response status: {response.status_code}")

            if response.status_code == 200:
                self.succ_request_counter += 1
                print(f"Successful request counter: {self.succ_request_counter}")

                folder = config.get("AUDIO_FOLDER")
                os.makedirs(folder, exist_ok=True)
                file_path = os.path.join(folder, f"{self.request_counter}.wav")

                # save audio file
                with open(file_path, "wb") as f:
                    f.write(response.content)
                print(f"[DOWNLOADER] saved: {file_path}")

                # add file path to audio queue instead of bulky response object
                self.add(file_path, "audio")
            else:
                print(f"Kokoro server error: {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
        finally:
            # always complete task to prevent deadlocks
            try:
                self.download_queue.task_done()
            except ValueError:
                pass

    @profiler.time_profile
    def download(self):
        while config.running:
            try:
                # small timeout to prevent cpu and queue spamming
                download_task = self.download_queue.get(timeout=0.5) # TODO timeout what to set it to

                # stop downloading if thread stop event is called
                if config.download_stop_event.is_set():
                    self.download_queue.task_done()
                    # config.download_stop_event.clear() # TODO add or remove?
                    continue

                self.dl(download_task)
            except queue.Empty:
                continue

    @profiler.time_profile
    def play_audio(self):
        while config.running:
            try:
                # small timeout to prevent cpu and queue spamming
                file_path = self.audio_queue.get(timeout=0.5)

                # stop playing if thread stop event is called
                if config.audio_stop_event.is_set():
                    self.audio_queue.task_done()
                    config.audio_stop_event.clear()
                    continue

                if os.path.exists(file_path):
                    print(f"Playing audio file: {file_path}")
                    data, fs = sf.read(file_path)

                    sd.play(data, fs)
                    self.audio_played_counter += 1
                    print(f"Audio count: {self.audio_played_counter}")

                    # interrupt instantly if stop event called
                    while sd.get_stream().active:
                        if config.audio_stop_event.is_set():
                            sd.stop()
                            break
                        elif not config.running: # TODO remove? redundant and not proper way to check in threads?
                            sd.stop()
                            break

                        # time.sleep(0.05) # TODO cause of small static if no audio queued?

                    print(f"Finished playing: {file_path}")

                self.audio_queue.task_done()
            except queue.Empty:
                continue

    def setDownloader(self):
        # check if thread exists and is currently alive
        if not self.downloader or not self.downloader.is_alive():
            self.downloader = threading.Thread(target=self.download, daemon=True)
            self.downloader.start()

    def setAudioPlayer(self):
        # check if thread exists and is currently alive
        if not self.audio_player or not self.audio_player.is_alive():
            self.audio_player = threading.Thread(target=self.play_audio, daemon=True)
            self.audio_player.start()


# init global singleton instance
q = _QueueHandler()