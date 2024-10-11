import os
import tempfile

from uparse.schema import Document

from ..pipeline import BaseTransform, Pipeline, State
from .utils import WHISPER_DEFAULT_SETTINGS, transcribe


class MediaState(State):
    pass


class ParseAudio(BaseTransform[MediaState]):
    async def transform(self, state, **kwargs):
        input_data = state["uri"]
        try:
            if isinstance(input_data, bytes):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
                    temp_audio_file.write(input_data)
                    temp_audio_path = temp_audio_file.name
            elif isinstance(input_data, str) and os.path.isfile(input_data):
                temp_audio_path = input_data
            else:
                raise ValueError(
                    "Invalid input data format. Expected audio bytes or audio file path."
                )

            # Transcribe the audio file
            transcript = transcribe(
                audio_path=temp_audio_path,
                whisper_model=self.shared.whisper_model,
                **WHISPER_DEFAULT_SETTINGS,
            )

            state["doc"] = Document(summary=transcript["text"])
            return state
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)


class ParseVideo(BaseTransform[MediaState]):
    async def transform(self, state, **kwargs):
        from moviepy.editor import VideoFileClip

        input_data = state["uri"]
        try:
            if isinstance(input_data, bytes):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
                    temp_video_file.write(input_data)
                    video_path = temp_video_file.name
            elif isinstance(input_data, str) and os.path.isfile(input_data):
                video_path = input_data
            else:
                raise ValueError(
                    "Invalid input data format. Expected video bytes or video file path."
                )

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
                whisper_model=self.shared.whisper_model,
                **WHISPER_DEFAULT_SETTINGS,
            )

            state["doc"] = Document(summary=transcript["text"])
            return state

        finally:
            # Clean up the temporary files
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)


class AudioPipeline(Pipeline):
    allowed_extensions = [".wav", ".mp3", ".m4a", ".mpeg", ".webm", ".mpga"]

    def __init__(self, *args, **kwargs):
        super().__init__(transforms=[ParseAudio()], *args, **kwargs)


class VideoPipeline(Pipeline):
    allowed_extensions = [".mp4"]

    def __init__(self, *args, **kwargs):
        super().__init__(transforms=[ParseVideo()], *args, **kwargs)