# Minimal type stub for faster-whisper.
# Provides enough type information for Pyright/JetBrains to resolve the
# import without requiring the full package stubs.
from typing import Any, Generator, Iterator, List, Optional, Tuple

class TranscriptionInfo:
    language: str
    language_probability: float
    duration: float

class Word:
    start: float
    end: float
    word: str
    probability: float

class Segment:
    id: int
    seek: int
    start: float
    end: float
    text: str
    tokens: List[int]
    temperature: float
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float
    words: Optional[List[Word]]

class WhisperModel:
    def __init__(
        self,
        model_size_or_path: str,
        device: str = "auto",
        device_index: int = 0,
        compute_type: str = "default",
        cpu_threads: int = 0,
        num_workers: int = 1,
        download_root: Optional[str] = None,
        local_files_only: bool = False,
    ) -> None: ...

    def transcribe(
        self,
        audio: Any,
        language: Optional[str] = None,
        task: str = "transcribe",
        beam_size: int = 5,
        **kwargs: Any,
    ) -> Tuple[Iterator[Segment], TranscriptionInfo]: ...

