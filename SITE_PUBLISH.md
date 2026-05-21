# ANA MAX Website Publish

Use the GitHub Pages URL for demos and public sharing. Do not share local
file-preview URLs from your machine.

## Public URL

```text
https://gyodragos-cell.github.io/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/
```

## One-Time GitHub Setup

1. Open the repository on GitHub.
2. Go to `Settings -> Pages`.
3. Set `Source` to `GitHub Actions`.
4. Save.

After that, every push to `main` publishes the website automatically through:

```text
.github/workflows/pages.yml
```

## Local Preview

For local testing, avoid opening `index.html` directly if you want a clean URL.
Run this from the repository root:

```powershell
python -m http.server 8080
```

Then open:

```text
http://127.0.0.1:8080/
```

## Before Publishing

Check:

```powershell
python -m compileall -q main.py core tools vscode_extension
python main.py --test
python main.py --list-tools
```

Website checks:

- buttons open the right section or tab
- Runtime WorkGraph nodes are clickable
- copy buttons work
- demo video loads or is intentionally replaced later
- no local machine paths or file-preview links are in public HTML/docs
