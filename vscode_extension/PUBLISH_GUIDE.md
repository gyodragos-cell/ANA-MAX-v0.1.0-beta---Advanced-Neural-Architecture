# 📦 ANA MAX Extension - Publishing Guide

## Current Status (v0.1.2)

✅ **Fixed Issues:**
- Version updated from 0.1.1 to 0.1.2
- Added missing `icon.png` (256x256 placeholder - replace with proper icon)
- Added `homepage` and `bugs` URLs to package.json

⚠️ **What Needs to Be Done:**

## Step 1: Replace Icon with Proper Design

The current `icon.png` is a placeholder. You need a proper 256x256 PNG icon.

**Requirements:**
- Size: 256x256 pixels (or 128x128)
- Format: PNG
- Background: Transparent or solid color
- Design: Something representing AI/neural network/brain

**How to create:**
- Use tools like Figma, Canva, or GIMP
- Or use an AI image generator (DALL-E, Midjourney, etc.)
- Search for "neural network icon" or "AI brain icon"

## Step 2: Install VSCE (VS Code Extension Manager)

```powershell
npm install -g @vscode/vsce
```

## Step 3: Create Microsoft Account & Publisher

1. Go to https://marketplace.visualstudio.com/manage/publishers
2. Sign in with Microsoft account (create one if needed)
3. Create a new publisher:
   - **Publisher ID**: Choose a unique name (e.g., `ana-max-team`, `neural-arch`)
   - **Display Name**: "ANA MAX Team" or your name
   - **Personal Access Token (PAT)**: Generate one with "Marketplace" scope

## Step 4: Update package.json with Your Publisher ID

Replace the publisher field in `package.json`:

```json
"publisher": "your-publisher-id-here"
```

**Important:** The publisher ID must match the one you created in Step 3.

## Step 5: Test Package Locally

```powershell
cd vscode_extension

# Validate the package
vsce ls

# Create .vsix file
vsce package

# This will create: advanced-neural-architecture-0.1.2.vsix
```

## Step 6: Publish to Marketplace

### Option A: Interactive Login
```powershell
vsce login your-publisher-id

# Enter your PAT when prompted
vsce publish
```

### Option B: Using PAT directly
```powershell
vsce publish -p YOUR_PERSONAL_ACCESS_TOKEN
```

## Step 7: Verify Publication

1. Go to https://marketplace.visualstudio.com/manage
2. Check "My Extensions" tab
3. You should see "ANA MAX - Advanced Neural Architecture"
4. Search in VS Code: Extensions → Search "ANA MAX"

## Step 8: Update and Republish (Future Updates)

```powershell
# 1. Update version in package.json (e.g., 0.1.3)
# 2. Make your changes
# 3. Package and publish
vsce package
vsce publish
```

## Common Issues & Solutions

### Issue: "Publisher already exists"
**Solution:** Choose a different publisher ID or use the existing one.

### Issue: "Personal access token invalid"
**Solution:** 
- Regenerate PAT with correct scopes (Marketplace)
- Make sure PAT hasn't expired

### Issue: "Extension already exists"
**Solution:** You can only publish once per name+publisher combo. Change version number for updates.

### Issue: "Missing icon"
**Solution:** Make sure `icon.png` exists in the extension root directory.

### Issue: "vsce not found"
**Solution:** Install with `npm install -g @vscode/vsce`

## Alternative: Publish to Open VSX

If you want to support VSCodium users:

```powershell
npm install -g ovsx
ovsx publish -p YOUR_OVSX_TOKEN
```

## Marketing Your Extension

After publishing:

1. **Update README.md** with installation instructions
2. **Add badges** to your main README:
   ```markdown
   [![Install](https://img.shields.io/badge/VS%20Marketplace-Install-blue)](https://marketplace.visualstudio.com/items?itemName=YOUR_PUBLISHER_ID.advanced-neural-architecture)
   ```
3. **Share on social media** (Twitter, LinkedIn, Reddit)
4. **Post on GitHub Discussions**
5. **Add to awesome lists** (awesome-vscode, awesome-mcp)

## Support & Contact

- **GitHub Issues:** https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture/issues
- **Email:** gyodragos@gmail.com

---

**Last Updated:** 2026-05-15
**Current Version:** 0.1.2