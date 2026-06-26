from typing import Optional

from google.adk.tools import ToolContext
from google.genai import types

from ...clients.tts import TTSClient
from ...core.models import TTSVoice, TTSSResponseFormat


def make_tts_tools(client: TTSClient, **kwargs) -> list:
    """Return ADK-compatible tool functions backed by a TTSClient."""

    async def synthesize_speech(
        text: str,
        tool_context: ToolContext,
        voice: str = "alloy",
        output_filename: Optional[str] = None,
    ) -> dict:
        """Convert text to speech and save the audio as an artifact.

        Args:
            text: The text to synthesize.
            voice: Voice name — one of alloy, echo, fable, onyx, nova, shimmer.
            output_filename: Artifact filename for the audio. Defaults to
                'speech_{voice}.mp3'.

        Returns:
            dict with 'artifact' (filename) and 'bytes' (audio length).
        """
        resp = await client.synthesize_async(text, voice=TTSVoice(voice))

        filename = output_filename or f"speech_{voice}.mp3"
        await tool_context.save_artifact(
            filename=filename,
            artifact=types.Part(
                inline_data=types.Blob(data=resp.audio_data, mime_type=resp.content_type)
            ),
        )

        return {"artifact": filename, "bytes": len(resp.audio_data)}

    return [synthesize_speech]
