# Session Checkpoint - 2026-06-04T16:09:27+00:00

## Deco theme deploy paused and regression fixes prepared

## Summary

Paused WordPress theme deploy after user reported v1.0.0 regressions. Installed PHP 8.4 CLI via winget and verified PHP lint. Fixed local theme text/grammar in page-cos.php, single-produse.php, front-page.php, archive-produse.php, and functions.php. Restored package to rely on existing GLightbox from custom-shop-plugin instead of custom lightbox JS. Added CSS regression layer to keep product images compact and restore subtle hover zoom. Rebuilt clean theme ZIP with hero images included and no scripts/secrets/plugin files.

## Current Goal

Stabilize Deco WordPress theme before upload; compare live/original behavior and avoid deploying a worse v1.0.0.

## Next Steps

- Visually compare current live pages to fixed package behavior
- decide upload or rollback. After theme is stable, design Phase Courier Integration: provider choice Fan Courier or Sameday, API credentials via environment/config, create shipment draft after order, keep fallback email-only order flow.

## Files Changed

- C:\Users\billy\Desktop\deco\page-cos.php
- C:\Users\billy\Desktop\deco\single-produse.php
- C:\Users\billy\Desktop\deco\front-page.php
- C:\Users\billy\Desktop\deco\archive-produse.php
- C:\Users\billy\Desktop\deco\functions.php
- C:\Users\billy\Desktop\deco\assets\css\performance.css
- C:\Users\billy\Desktop\deco\style-shop.css
- C:\Users\billy\Desktop\deco\assets\js\frontend-ui.js
- C:\Users\billy\Desktop\handmade-decor-luxury-v1.0.0-wp.zip

## Validation

```text
PHP lint PASS on all root PHP files in C:\Users\billy\Desktop\deco using PHP 8.4.22. JS syntax check PASS for assets/js/frontend-ui.js. ZIP checks PASS: style.css present, Version 1.0.0, hero images present, forbidden_count 0, no backslash paths. Unicode checks PASS for key UI strings in ZIP.
```

## Risks

- Do not upload yet until Billy visually checks staging/live after upload. Local Desktop only has current deco and deco_release_v1.0.0, no older backup folder found. Live site currently uses GLightbox from custom-shop-plugin
- plugin must remain active. Courier integration with Fan Courier/Sameday is a separate business/API phase and requires provider account/API details stored outside code.

## Lab/Release Sync Status

Private Deco site work; not public release.
