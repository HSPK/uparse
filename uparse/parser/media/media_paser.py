import os
import tempfile

from moviepy.editor import VideoFileClip

from uparse.types import Document

from .._base import BaseParser
from .utils import WHISPER_DEFAULT_SETTINGS, transcribe


def parse_audio(input_data, model_state) -> Document:
    try:
        if isinstance(input_data, bytes):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
                temp_audio_file.write(input_data)
                temp_audio_path = temp_audio_file.name
        elif isinstance(input_data, str) and os.path.isfile(input_data):
            temp_audio_path = input_data
        else:
            raise ValueError("Invalid input data format. Expected audio bytes or audio file path.")

        # Transcribe the audio file
        transcript = transcribe(
            audio_path=temp_audio_path,
            whisper_model=model_state.whisper_model,
            **WHISPER_DEFAULT_SETTINGS,
        )

        return Document(summary=transcript["text"])

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


def parse_video(input_data, model_state) -> Document:
    try:
        if isinstance(input_data, bytes):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
                temp_video_file.write(input_data)
                video_path = temp_video_file.name
        elif isinstance(input_data, str) and os.path.isfile(input_data):
            video_path = input_data
        else:
            raise ValueError("Invalid input data format. Expected video bytes or video file path.")

        # Extract audio from the video
        audio_path = (
            f"{tempfile.gettempdir()}/{os.path.splitext(os.path.basename(video_path))[0]}.mp3"
        )
        video_clip = VideoFileClip(video_path)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(audio_path)
        audio_clip.close()
        video_clip.close()

        # Transcribe the audio file
        transcript = transcribe(
            audio_path=audio_path,
            whisper_model=model_state.whisper_model,
            **WHISPER_DEFAULT_SETTINGS,
        )

        return Document(summary=transcript["text"])

    finally:
        # Clean up the temporary files
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)


class AudioParser(BaseParser):
    allowed_extensions = [".wav", ".mp3", ".m4a", ".mpeg", ".webm", ".mpga"]

    def __init__(self, uri, model_state, **kwargs):
        super().__init__(uri)
        self.model_state = model_state

    def parse(self) -> Document:
        return parse_audio(self.uri, self.model_state)


class VideoParser(BaseParser):
    allowed_extensions = [".mp4"]

    def __init__(self, uri, model_state, **kwargs):
        super().__init__(uri)
        self.model_state = model_state

    def parse(self) -> Document:
        return parse_video(self.uri, self.model_state)
