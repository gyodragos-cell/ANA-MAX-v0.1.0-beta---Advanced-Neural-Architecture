# 📋 GitHub & Marketplace Publish Checklist

## Pre-Release (Local Verification)

- [ ] `python main.py --test` → 2/2 PASS
- [ ] `python main.py --list-tools` → 42 tools listed
- [ ] `npm pack --dry-run` în `vscode_extension/` → ✅ valid
- [ ] `.env` not in repo (check `.gitignore`)
- [ ] `.env.example` has placeholders only
- [ ] No API keys in code comments
- [ ] `README.md` is up-to-date

---

## GitHub Repository Setup

### 1. Create GitHub Repository
```
https://github.com/YOUR_USERNAME/ana-max
```

### 2. Configure Repository Settings
- [ ] Description: "AI-powered Windows automation with 42 MCP tools"
- [ ] Topics: `mcp`, `windows-automation`, `ai-tools`, `desktop-control`, `python`
- [ ] Make Public
- [ ] Add license: MIT

### 3. Push Code
```powershell
cd ANA_MAX_GitHub_Release

git init
git add .
git commit -m "Initial release: ANA MAX v18.0-TRIAL with 42 tools"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ana-max.git
git push -u origin main
```

### 4. Create Release
- [ ] Go to GitHub → Releases → Draft new release
- [ ] Tag: `v18.0-trial`
- [ ] Title: `ANA MAX v18.0 - Trial Release (42 Free Tools)`
- [ ] Description:
```
## Features
- 42 free MCP tools for Windows automation
- Windows UI Automation (pywinauto)
- Browser control and web scraping
- Git operations and code analysis
- Terminal with persistent session
- Network diagnostics and security audit

## What's Included (FREE)
✅ File operations, code tools, web search
✅ System monitoring, git control
✅ Browser automation, terminal
✅ Windows UI Automation
✅ Security audit, smart search
✅ ADB for Android, Frida instrumentation

## What's NOT Included (Premium)
❌ Desktop capture (requires license)
❌ Live desktop viewer (premium)
❌ Desktop control advanced (pro)
❌ Windows Deep Sight (God View)

See INSTALL_GUIDE.md for full setup.
```
- [ ] Attach `ana-max-18.0-trial.zip`
- [ ] Publish Release

---

## VS Code Marketplace

### Prerequisites
```powershell
npm install -g vsce
```

### 1. Create Publisher Account
- [ ] https://marketplace.visualstudio.com/manage/publishers
- [ ] Create new publisher (e.g., `your-name`)
- [ ] Generate PAT (Personal Access Token)

### 2. Update Extension Metadata
Edit `vscode_extension/package.json`:
```json
{
  "publisher": "your-name",
  "name": "ana-max",
  "displayName": "ANA MAX - Advanced Neural Architecture",
  "version": "0.1.0",
  "repository": {
    "type": "git",
    "url": "https://github.com/YOUR_USERNAME/ana-max"
  }
}
```

### 3. Package & Publish
```powershell
cd vscode_extension

# Login to publisher
vsce login your-name

# Package
vsce package

# Publish
vsce publish

# Or publish specific version
vsce publish 0.1.0
```

### 4. Verify in Marketplace
- [ ] Search "ana-max" in VS Code Extensions
- [ ] Install and test locally
- [ ] Check page: marketplace.visualstudio.com/items?itemName=your-name.ana-max

---

## Documentation Checklist

### Root Files
- [ ] `README.md` - Overview & quick start
- [ ] `SETUP_AND_RUN.md` - Detailed setup guide
- [ ] `INSTALL_GUIDE.md` - Installation instructions
- [ ] `CHANGELOG.md` - Version history
- [ ] `LICENSE` - MIT license
- [ ] `.env.example` - Environment template

### Code Documentation
- [ ] `core/` - Core logic documented
- [ ] `tools/` - Tool-specific READMEs
- [ ] `docs/PROJECT_MAP_AI_GUIDE.md` - Architecture

### Extension Documentation
- [ ] `vscode_extension/README.md` - Extension guide

---

## Announce Release

- [ ] Post on GitHub Discussions
- [ ] Tweet/LinkedIn: "ANA MAX released with 42 free tools for Windows automation"
- [ ] Add to Awesome lists (awesome-mcp, awesome-windows-automation)

---

## Post-Launch Monitoring

- [ ] Monitor GitHub Issues
- [ ] Check marketplace ratings
- [ ] Fix bugs quickly
- [ ] Plan v19.0 with premium tools

---

## Versioning Strategy

| Version | Release Type | Premium Tools |
|---------|-------------|---------------|
| 18.0-trial | Public Trial | ❌ Disabled |
| 18.0-pro | Paid License | ✅ Enabled |
| 19.0 | Feature Update | TBD |

---

**Current Status:** Ready for GitHub release ✅
**Next:** Deploy to GitHub + VS Code Marketplace
