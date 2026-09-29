"""Debug: why does _select_tool_names return code_tools for 'salut ce faci?'"""
from core.backends.ollama_backend import _select_tool_names, _KEYWORD_TO_TOOLS, _ALWAYS_TOOLS

msg = "salut ce faci?"
lowered = msg.lower()
words = set(lowered.split())

print(f"Message: {msg}")
print(f"Words: {words}")
print(f"Always tools: {_ALWAYS_TOOLS}")
print(f"Result: {_select_tool_names(msg)}")
print()

for keywords, tool_names in _KEYWORD_TO_TOOLS:
    word_match = keywords & words
    substr_match = [kw for kw in keywords if kw in lowered]
    if word_match or substr_match:
        print(f"MATCH -> tools={tool_names}")
        print(f"  Word match: {word_match}")
        print(f"  Substr match: {substr_match}")
