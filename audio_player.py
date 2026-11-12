from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sounddevice as sd
from pydub import AudioSegment

AUDIO_FORMATS = frozenset({"pcm", "wav", "mp3"})


@dataclass(frozen=True, slots=True)
class AudioClip:
    path: Path
    format: str
    sample_rate: int | None = None
    channels: int = 1
    sample_width: int = 2

    def __post_init__(self) -> None:
        audio_format = self.format.lower()
        if audio_format not in AUDIO_FORMATS:
            raise ValueError(f"Unsupported audio format: {self.format}")
        object.__setattr__(self, "format", audio_format)

        if self.channels < 1:
            raise ValueError("AudioClip channels must be at least 1")

        if audio_format == "pcm":
            if self.sample_rate is None or self.sample_rate <= 0:
                raise ValueError("PCM clips require a positive sample_rate")
            if self.sample_width not in {1, 2, 3, 4}:
                raise ValueError("AudioClip sample_width must be 1, 2, 3, or 4 bytes")


class AudioPlayer:
    def __init__(self, *, maxsize: int = 100) -> None:
        self.audio_queue: queue.Queue[AudioClip] = queue.Queue(maxsize=maxsize)
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._skip_event = threading.Event()
        self._state_lock = threading.Lock()
        self._playing = False
        self.played = 0

    @property
    def running(self) -> bool:
        worker = self._worker
        return worker is not None and worker.is_alive()

    @property
    def qsize(self) -> int:
        return self.audio_queue.qsize()

    def start(self) -> None:
        if self.running:
            return

        self._stop_event.clear()
        self._skip_event.clear()
        self._worker = threading.Thread(target=self._run, name="audio-player", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        worker = self._worker
        if worker is None:
            return

        self._stop_event.set()
        sd.stop()
        
        if worker is not threading.current_thread():
            worker.join(timeout=1.0)
        if not worker.is_alive():
            self._worker = None

    def skip(self) -> bool:
        with self._state_lock:
            if not self._playing:
                return False

        self._skip_event.set()
        sd.stop()
        return True

    def add(self, clip: AudioClip) -> None:
        self.audio_queue.put(clip)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                clip = self.audio_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            try:
                if self._stop_event.is_set():
                    break
                if self._play(clip):
                    self.played += 1
            finally:
                self.audio_queue.task_done()

    def _play(self, clip: AudioClip) -> bool:
        try:
            samples, sample_rate = self._decode(clip)
        except Exception as error:
            print(f"[AUDIO] Failed to decode {clip.path}: {error}")
            return False

        with self._state_lock:
            self._playing = True

        try:
            sd.play(samples, sample_rate)
            sd.wait()
        except Exception as error:
            print(f"[AUDIO] Playback failed for {clip.path}: {error}")
            return False
        finally:
            with self._state_lock:
                self._playing = False
            interrupted = self._stop_event.is_set() or self._skip_event.is_set()
            self._skip_event.clear()

        return not interrupted

    @staticmethod
    def _decode(clip: AudioClip) -> tuple[np.ndarray, int]:
        if clip.format == "pcm":
            if clip.sample_rate is None:
                raise ValueError("PCM clips require a sample rate")
            segment = AudioSegment(
                data=clip.path.read_bytes(),
                sample_width=clip.sample_width,
                frame_rate=clip.sample_rate,
                channels=clip.channels,
            )
        else:
            with clip.path.open("rb") as audio_file:
                segment = AudioSegment.from_file(audio_file, format=clip.format)

        samples = np.array(segment.get_array_of_samples())
        if segment.channels > 1:
            samples = samples.reshape((-1, segment.channels))

        return samples, segment.frame_rate
