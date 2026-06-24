import queue


class AudioHandler():
    def __init__(self):
        self.audio_queue = queue.Queue(maxsize=100)  # TODO configurable
        self.audio_player = None
        self.audio_played_counter = 0
        self.buffer = 0
        self.buffer_threshold = 5000 # ms
        chunk_size = 2048 # for possible audio streaming, not currently using