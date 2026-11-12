import io
import queue
import threading
from pathlib import Path

from openai import APIConnectionError, APIStatusError
from pydub import AudioSegment

from audio_player import AUDIO_FORMATS, AudioClip, AudioPlayer
from config_handler import config
from profiler import profiler
from voice_engine import voice_engine


class _QueueHandler():
    def __init__(self) -> None:
        self.download_queue: queue.Queue[dict[str, str]] = queue.Queue(10)
        self.ocr_queue: queue.Queue[object] = queue.Queue(50)
        self.downloader: threading.Thread | None = None
        self.ocr_worker: threading.Thread | None = None
        self.audio_player = AudioPlayer()
        self.request_counter = 0
        self.succ_request_counter = 0

        # set global events for easy start/stop
        self.download_stop_event = threading.Event()
        self.ocr_worker_stop_event = threading.Event()

    @property
    def audio_queue(self) -> queue.Queue[AudioClip]:
        return self.audio_player.audio_queue

    @property
    def audio_played_counter(self) -> int:
        return self.audio_player.played


    # call resume instead?
    # start all queues and worker threads
    @profiler.time_profile
    def start(self) -> None:
        # prevent duplicate toggles
        if not config.running:
            print('Starting Queue worker')
            config.running = True
            self.download_stop_event.clear()

            self.setDownloader()
            self.audio_player.start()

            print(f'Resuming: {config.running}')

        # only start OCR if component enabled
        if config.ocr:
            self.setOcrWorker()
            self.ocr_worker_stop_event.clear()
        else:
            print("NOT starting OCR since its disabled")

    @profiler.time_profile
    def stop(self) -> None:
        # prevent duplicate toggles
        if config.running:
            print('Pausing/Stopping Queue workers/threads')
            config.running = False
            self.download_stop_event.set()
            self.ocr_worker_stop_event.set()
            self.audio_player.stop()

        config.running = False
        print(f'Stopped: {config.running}')

    @profiler.time_profile
    def skip(self) -> None:
        self.audio_player.skip()
        print('Skipping')

    @profiler.time_profile
    def disable_ocr(self) -> None:
        if config.ocr:
            print('[Queue] Disabling OCR')
            self.ocr_worker_stop_event.set()
            config.ocr = False

    @profiler.time_profile
    def add_smooth_fade(self, raw_audio_bytes: bytes, audio_format: str) -> bytes:
        try:
            if audio_format == "pcm":
                if voice_engine.sample_rate is None:
                    raise ValueError("PCM audio requires a sample rate")
                audio = AudioSegment(
                    data=raw_audio_bytes,
                    sample_width=voice_engine.sample_width,
                    frame_rate=voice_engine.sample_rate,
                    channels=voice_engine.channels,
                )
            else:
                audio = AudioSegment.from_file(io.BytesIO(raw_audio_bytes), format=audio_format)

            # short fade in and out to remove static/crackling at end
            smoothed_audio = audio.fade_in(50).fade_out(50)

            if audio_format == "pcm":
                return smoothed_audio.raw_data

            # Preserve the response's encoded format when exporting the faded audio.
            audio_bytes = io.BytesIO()
            smoothed_audio.export(audio_bytes, format=audio_format)

            return audio_bytes.getvalue()

        except Exception as e:
            print(f"[AUDIO] ERROR Failed to smooth audio: {e}")
            return raw_audio_bytes  # return original in case of error

    def add(self, item: object, item_type: str) -> None:
        print(f"Adding {item_type} to queue: {item}")
        if item_type == 'audio':
            if not isinstance(item, AudioClip):
                raise TypeError("Audio queue items must be AudioClip instances")
            self.audio_player.add(item)
            print(f"{item_type} queue size: {self.audio_player.qsize}")
        elif item_type == 'download':
            if not isinstance(item, dict):
                raise TypeError("Download queue items must be dictionaries")
            self.download_queue.put(item)
            print(f"{item_type} queue size: {self.download_queue.qsize()}")
        elif item_type == 'ocr':
            self.ocr_queue.put(item)
            print(f"{item_type} queue size: {self.ocr_queue.qsize()}")

    @profiler.time_profile
    def dl(self, download_task: dict[str, str]) -> None:
        try:
            self.request_counter += 1
            print(f"Request counter: {self.request_counter}")

            audio_bytes = voice_engine.synthesize(download_task["text"], download_task["voice"])
            self.succ_request_counter += 1
            print(f"Successful request counter: {self.succ_request_counter}")

            folder = Path(config.get("AUDIO_FOLDER") or "saved_audio")
            folder.mkdir(parents=True, exist_ok=True)
            audio_format = voice_engine.response_format.lower()
            if audio_format not in AUDIO_FORMATS:
                raise ValueError(f"Unsupported audio response format: {audio_format}")
            file_path = folder / f"{self.request_counter}.{audio_format}"

            # add audio fade if no or low audio queue
            if self.audio_player.qsize <= 2:
                print(f"[DOWNLOADER] adding audio fade to file: {file_path}, audio queue: {self.audio_player.qsize}")
                audio_bytes = self.add_smooth_fade(audio_bytes, audio_format)

            # save audio file # TODO make optional, on with debug and also config and GUI option
            file_path.write_bytes(audio_bytes)
            print(f"[DOWNLOADER] saved: {file_path}")

            clip = AudioClip(
                path=file_path,
                format=audio_format,
                sample_rate=voice_engine.sample_rate,
                channels=voice_engine.channels,
                sample_width=voice_engine.sample_width,
            )
            self.add(clip, "audio")
        except APIConnectionError as e:
            print(f"{config.active_tts_api} Connection Error: {e}")
        except APIStatusError as e:
            print(f"{config.active_tts_api} Server Error: {e.status_code}: {e.message}")
        except Exception as e:
            print(f"[DOWNLOADER] ERROR: {e}")
        finally:
            # always complete task to prevent deadlocks
            try:
                self.download_queue.task_done()
            except ValueError:
                pass

    @profiler.time_profile
    def download(self) -> None:
        while config.running:
            # Check the stop event BEFORE pulling an item out of the queue
            if self.download_stop_event.is_set():
                break  # Exit the loop instantly without modifying queue items

            try:
                # small timeout to prevent cpu and queue spamming
                download_task = self.download_queue.get(timeout=0.5) # TODO timeout what to set it to

                # stop downloading if thread stop event is called
                if self.download_stop_event.is_set():
                    # Return the item to the queue so it isn't lost
                    self.download_queue.put(download_task)
                    # Tell the queue we are releasing our lock on this specific fetch operation
                    self.download_queue.task_done()
                    break



                self.dl(download_task)
            except queue.Empty:
                continue

    @profiler.time_profile
    def process_ocr_queue(self) -> None:
        import ocr

        while config.running and config.ocr and not self.ocr_worker_stop_event.is_set():
            try:
                # small timeout to prevent cpu and queue spamming
                ocr_task = self.ocr_queue.get(timeout=0.1) # TODO timeout what to set it to

                try:
                    if self.ocr_worker_stop_event.is_set():
                        continue
                    ocr.run_ocr(ocr_task, False)
                finally:
                    self.ocr_queue.task_done()
            except queue.Empty:
                continue

    def setDownloader(self) -> None:
        # check if thread exists and is currently alive
        if not self.downloader or not self.downloader.is_alive():
            print(f"Starting downloader thread...")
            self.downloader = threading.Thread(target=self.download, daemon=True)
            self.downloader.start()

    def setAudioPlayer(self) -> None:
        self.audio_player.start()

    def setOcrWorker(self) -> None:
        if config.ocr and (self.ocr_worker is None or not self.ocr_worker.is_alive()):
            print(f"Starting OCR thread...")
            # TODO target?
            self.ocr_worker = threading.Thread(target=self.process_ocr_queue, daemon=True)
            self.ocr_worker.start()


# init global singleton instance
q = _QueueHandler()