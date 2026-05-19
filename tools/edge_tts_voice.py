"""
ANA MAX - Voice Tool

Small registry wrapper for local voice commentary. It is intentionally safe for
the public release: if no TTS engine is installed, the tool reports disabled
instead of failing registration.
"""

from __future__ import annotations

from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


class EdgeTTSVoice(Tool):
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="edge_tts_voice",
            description="Local voice commentary for ANA MAX status/progress messages.",
            parameters=[
                ToolParameter(
                    name="action",
                    description="Action to perform",
                    type="string",
                    required=True,
                    choices=["status", "speak", "enable", "disable", "toggle"],
                ),
                ToolParameter(
                    name="text",
                    description="Text to speak when action=speak",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="block",
                    description="Wait until speaking completes",
                    type="boolean",
                    required=False,
                    default=False,
                ),
            ],
            category="voice",
        )

    def execute(self, action: str, text: str = "", block: bool = False, **kwargs) -> ToolResult:
        try:
            from tools.voice_commentary import TTS_AVAILABLE, get_commentary

            commentary = get_commentary(enabled=False)

            if action == "status":
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"tts_available": TTS_AVAILABLE, "enabled": commentary.enabled},
                    message="Voice available" if TTS_AVAILABLE else "Voice disabled: pyttsx3 is not installed",
                )

            if action == "enable":
                commentary.enable()
                return ToolResult(status=ToolStatus.SUCCESS, data={"enabled": commentary.enabled})

            if action == "disable":
                commentary.disable()
                return ToolResult(status=ToolStatus.SUCCESS, data={"enabled": commentary.enabled})

            if action == "toggle":
                return ToolResult(status=ToolStatus.SUCCESS, data={"enabled": commentary.toggle()})

            if action == "speak":
                if not text:
                    return ToolResult(status=ToolStatus.ERROR, error="Text is required for speak")
                commentary.speak(text, block=bool(block))
                return ToolResult(status=ToolStatus.SUCCESS, data={"spoken": commentary.enabled}, message=text)

            return ToolResult(status=ToolStatus.ERROR, error=f"Unknown action: {action}")
        except Exception as exc:
            return ToolResult(status=ToolStatus.ERROR, error=str(exc))
