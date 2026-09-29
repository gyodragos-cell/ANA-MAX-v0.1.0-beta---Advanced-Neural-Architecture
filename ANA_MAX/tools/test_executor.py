import subprocess, json, sys

steps = [
    "Search for Artificial General Intelligence",
    "Open the first article",
    "Scroll through the page",
    "Extract the first paragraph",
    "Navigate back",
    "Change language to German",
    "Repeat the search",
    "Open the first result",
    "Extract the first paragraph again"
]

subprocess.run([
    sys.executable,
    "tools/ana_ultrafast_web_executor_v3.py",
    "--goal", "Evaluate Next-Gen ANA browser automation",
    "--start_url", "https://www.wikipedia.org",
    "--steps", json.dumps(steps),
    "--headless",
])
