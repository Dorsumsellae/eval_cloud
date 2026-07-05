"""Service ASR isole : transcription (+ diarisation) de videos YouTube via WhisperX.

Pourquoi un service separe ? WhisperX epingle torch / transformers a des versions
incompatibles avec la stack RAG du backend (embeddings). On isole donc ces
dependances lourdes dans leur propre conteneur ; le backend l'appelle en HTTP
uniquement lorsqu'une video n'a pas de sous-titres exploitables.

Chaine : yt-dlp (audio) -> WhisperX transcribe -> alignement mot-a-mot
-> diarisation pyannote (optionnelle, si HF_TOKEN) -> segments {start,end,text,speaker}.
"""

import os
import shutil
import tempfile
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# --- Configuration (variables d'environnement) ------------------------------
ASR_MODEL = os.getenv("ASR_MODEL", "small")  # tiny/base/small/medium/large-v3
ASR_DEVICE = os.getenv("ASR_DEVICE", "cpu")  # cpu / cuda
ASR_COMPUTE_TYPE = os.getenv("ASR_COMPUTE_TYPE", "int8")  # int8 (CPU) / float16 (GPU)
# Jeton Hugging Face requis pour la diarisation pyannote (modele gated). Sans lui,
# on renvoie la transcription sans locuteurs.
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()

app = FastAPI(
    title="Service ASR (WhisperX)",
    description="Transcription + diarisation de videos YouTube sans sous-titres.",
    version="1.0.0",
)


class TranscribeRequest(BaseModel):
    video_id: str = Field(..., description="Identifiant de la video YouTube.")
    languages: list[str] | None = Field(
        None,
        description="Langues preferees ; si omis, Whisper detecte la langue parlee (originale).",
    )
    diarize: bool = Field(
        True, description="Activer la diarisation (necessite HF_TOKEN cote serveur)."
    )
    num_speakers: int | None = Field(
        None,
        ge=1,
        description=(
            "Nombre de locuteurs si connu. 1 = mono-locuteur : la diarisation est "
            "**ignoree** (plus rapide). >1 = contrainte passee a pyannote pour "
            "accelerer/fiabiliser. None = detection automatique du nombre."
        ),
    )


class Segment(BaseModel):
    start: float
    end: float
    text: str
    speaker: str | None = None


class TranscribeResponse(BaseModel):
    language: str = Field(..., description="Langue detectee/utilisee.")
    diarized: bool = Field(..., description="Vrai si des locuteurs ont ete attribues.")
    segments: list[Segment]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@lru_cache(maxsize=1)
def _asr_model():
    """Charge le modele WhisperX une seule fois (couteux)."""
    import whisperx

    return whisperx.load_model(ASR_MODEL, device=ASR_DEVICE, compute_type=ASR_COMPUTE_TYPE)


def _download_audio(video_id: str) -> tuple[str, str]:
    """Telecharge la piste audio de la video. Retourne (chemin_wav, dossier_temp)."""
    import yt_dlp

    workdir = tempfile.mkdtemp(prefix="asr_")
    url = f"https://www.youtube.com/watch?v={video_id}"
    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(workdir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        # Certains clients YouTube renvoient un 403 sur l'URL media ; les clients
        # 'android'/'ios' contournent ce blocage (pas de PO token requis).
        "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "wav"}
        ],
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    return os.path.join(workdir, f"{info['id']}.wav"), workdir


def _diarize(audio, result: dict, num_speakers: int | None) -> bool:
    """Attribue les locuteurs aux segments (best-effort). Retourne True si applique.

    `num_speakers` (>1) contraint pyannote au nombre connu de locuteurs, ce qui
    accelere et fiabilise la diarisation.
    """
    if not HF_TOKEN:
        return False
    try:
        import whisperx

        try:
            from whisperx.diarize import DiarizationPipeline
        except ImportError:  # emplacement selon la version de whisperx
            DiarizationPipeline = whisperx.DiarizationPipeline

        # whisperx 3.8.x : parametre 'token' (anciennement 'use_auth_token').
        pipeline = DiarizationPipeline(token=HF_TOKEN, device=ASR_DEVICE)
        kwargs = {"num_speakers": num_speakers} if num_speakers and num_speakers > 1 else {}
        diarize_segments = pipeline(audio, **kwargs)
        whisperx.assign_word_speakers(diarize_segments, result)
        return True
    except Exception:
        # La diarisation est un plus : en cas d'echec (modele gated non accepte,
        # RAM insuffisante...), on conserve la transcription sans locuteurs.
        return False


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe(req: TranscribeRequest) -> TranscribeResponse:
    """Telecharge l'audio, transcrit, aligne, et diarise si possible."""
    import whisperx

    try:
        audio_path, workdir = _download_audio(req.video_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Telechargement audio echoue : {exc}"
        ) from exc

    try:
        audio = whisperx.load_audio(audio_path)
        forced = req.languages[0] if req.languages else None
        result = _asr_model().transcribe(audio, batch_size=16, language=forced)
        language = result.get("language") or (forced or "")

        # Alignement mot-a-mot : ameliore la precision des timecodes (best-effort).
        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=language, device=ASR_DEVICE
            )
            result = whisperx.align(
                result["segments"], model_a, metadata, audio, ASR_DEVICE
            )
        except Exception:
            pass

        # Mono-locuteur (num_speakers == 1) : on saute la diarisation -> plus rapide.
        do_diarize = req.diarize and req.num_speakers != 1
        diarized = _diarize(audio, result, req.num_speakers) if do_diarize else False

        segments = []
        for seg in result.get("segments", []):
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            segments.append(
                Segment(
                    start=float(seg.get("start", 0.0)),
                    end=float(seg.get("end", seg.get("start", 0.0))),
                    text=text,
                    speaker=seg.get("speaker"),
                )
            )
        if not segments:
            raise HTTPException(status_code=422, detail="Transcription vide.")

        return TranscribeResponse(language=language, diarized=diarized, segments=segments)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
