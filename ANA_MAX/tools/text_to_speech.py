"""
Text-to-Speech Tool - Read agent output aloud
Citeste pe glas ce scriu eu

Author: Kiro
Date: 2026-05-19
"""

import pyttsx3
import threading
from typing import Optional
from tools.base import Tool, ToolDefinition, ToolParameter, ToolResult, ToolStatus


class TextToSpeechTool(Tool):
    """ Read text aloud using Windows SAPI"""
    
    def __init__(self) -> None:
        self.engine = pyttsx3.init()
        # Windows voices
        self.engine.setProperty('rate', 150)  # Speed (words per minute)
        self.engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="text_to_speech",
            description=" Read text aloud using Windows text-to-speech. Citeste textul pe glas.",
            parameters=[
                ToolParameter(
                    name="text",
                    description="Text to speak",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="wait",
                    description="Wait for speech to finish (true/false, default: false)",
                    type="boolean",
                    required=False
                ),
                ToolParameter(
                    name="rate",
                    description="Speech rate (50-200, default: 150)",
                    type="integer",
                    required=False
                ),
                ToolParameter(
                    name="volume",
                    description="Volume (0.0-1.0, default: 0.9)",
                    type="number",
                    required=False
                )
            ],
            category="interface",
            requires_confirmation=False,
            dangerous=False
        )
    
    def execute(self, text: str, wait: bool = False, rate: int = 150, volume: float = 0.9, **kwargs) -> ToolResult:
        """Speak text aloud"""
        try:
            # Set properties
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            
            # Say it
            self.engine.say(text)
            
            if wait:
                self.engine.runAndWait()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f" Spoke: {text[:50]}..."
                )
            else:
                # Non-blocking - say in background
                threading.Thread(target=self.engine.runAndWait, daemon=True).start()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f" Speaking: {text[:50]}..."
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"TTS failed: {e}"
            )
    
    def speak(self, text: str, wait: bool = False) -> None:
        """Simple speak function (no return value needed)"""
        self.engine.say(text)
        if wait:
            self.engine.runAndWait()
        else:
            threading.Thread(target=self.engine.runAndWait, daemon=True).start()
    
    def stop(self) -> None:
        """Stop speaking"""
        self.engine.stop()
    
    def set_voice(self, voice_index: int = 0) -> None:
        """
        Set voice (0 = default, 1+ = different voices)
        
        On Windows:
        - 0: Default voice
        - 1: Alternate voice (if available)
        """
        voices = self.engine.getProperty('voices')
        if voice_index < len(voices):
            self.engine.setProperty('voice', voices[voice_index].id)
    
    def list_voices(self) -> list:
        """Get available voices"""
        voices = self.engine.getProperty('voices')
        return [f"{i}: {v.name}" for i, v in enumerate(voices)]
