# ANA MAX - AI Workflow Rules

**Workspace root:** `C:\Users\billy\Desktop\ana_dev\`
**Main project:** `C:\Users\billy\Desktop\ana_dev\ANA_MAX\`
**Scrcpy + tools:** `C:\Users\billy\Desktop\scrcpy-win64-v3.3.4\`

Acest fisier defineste regula de lucru pentru orice AI sau asistent care modifica proiectul `ANA_MAX`.

##  Cuprins
- [Regula de baza](#regula-de-baza)
- [Regula anti-inventat](#regula-anti-inventat)
- [Ordinea obligatorie de lucru](#ordinea-obligatorie-de-lucru)
- [Ce nu are voie sa faca](#ce-nu-are-voie-sa-faca)
- [Stil de lucru recomandat](#stil-de-lucru-recomandat)
- [Prompt pentru alt AI](#prompt-scurt-pentru-alt-ai)

> [!NOTE]
> Scopul acestor reguli este sa lucram curat, sa urmam aceeasi ordine de pasi si sa pastram proiectul usor de inteles si reparat.

## Regula de baza

Orice AI care lucreaza in acest proiect trebuie sa:
- inteleaga contextul inainte sa editeze
- faca schimbari mici si clare
- verifice rezultatul dupa modificare
- documenteze ce a schimbat daca schimbarea are impact operational
- nu inventeze raspunsuri, cauze sau verificari atunci cand nu stie sigur

## Regula anti-inventat

> [!CAUTION]
> Daca nu stii, nu poti verifica sau nu esti sigur, SPUNE EXPLICIT. Nu inventa explicatii doar pentru a parea sigur.

Daca AI-ul:
- nu stie
- nu poate verifica
- nu gaseste fisierul sau contextul necesar
- nu este sigur de cauza unei probleme

atunci trebuie sa spuna explicit acest lucru.

Formulari bune:
- `Nu stiu inca, trebuie sa verific`
- `Nu pot confirma fara sa citesc fisierul X`
- `Nu am putut verifica acest pas`
- `Nu sunt suficient de sigur ca sa afirm asta`

AI-ul nu trebuie sa:
- inventeze explicatii doar ca sa para sigur
- spuna ca a verificat ceva daca nu a verificat
- prezinte presupuneri ca fapte
- ascunda incertitudinea

## Ordinea obligatorie de lucru

### 1. Citeste contextul minim

Inainte de modificari, AI-ul trebuie sa citeasca:
- `README.md`
- `QUICK_START_*.md`
- ultimul worklog din `docs/`

> [!IMPORTANT]
> Daca task-ul tine de setup sau reinstalare, trebuie sa verifice si scripturile de BOOTSTRAP si SETUP din radacina.

### 2. Inspecteaza exact zona afectata

AI-ul nu trebuie sa editeze din presupuneri.
Trebuie sa citeasca fisierele direct implicate si sa inteleaga conventiile existente.

### 3. Face schimbarea minima necesara

Reguli:
- nu rescrie fisiere mari daca e suficienta o modificare mica
- nu schimba stilul proiectului fara motiv
- nu adauga dependinte care dubleaza ceva deja standardizat

### 4. Pastreaza compatibilitatea

> [!WARNING]
> Evita ruperea fluxurilor existente. Daca un script vechi este folosit des, preferabil devine wrapper, nu este eliminat.

### 5. Verifica dupa schimbare

Dupa orice modificare, AI-ul trebuie sa faca verificarea minima utila:
1. Verificare de sintaxa sau continut
2. Rulare localizata a schimbarii
3. Smoke test sau test punctual daca e cazul

### 6. Documenteaza daca schimbarea conteaza operational

Actualizeaza `README.md` (vedere rapida) si `docs/WORKLOG_YYYY-MM-DD.md` (istoric).

## Ce nu are voie sa faca

AI-ul nu trebuie sa:
- stearga sau rescrie masiv fisiere fara motiv clar
- lase proiectul fara verificare minima
- schimbe formatterul sau stilul editorului fara acord explicit
- creeze fisiere noi fara sa aiba un rol clar

## Stil de lucru recomandat

Comportamentul dorit este: **calm, clar, incremental si orientat pe mentenanta.**

## Prompt scurt pentru alt AI

Poti da altui AI acest prompt:

```text
Lucrezi in proiectul ANA_MAX. Respecta fisierul AI_RULES.md.
Ordinea obligatorie este:
1. Citeste README.md, QUICK_START si ultimul worklog.
2. Inspecteaza fisierele direct afectate.
3. Fa schimbarea minima necesara, fara sa rupi fluxurile existente.
4. Pastreaza compatibilitatea scripturilor deja folosite.
5. Verifica schimbarea prin citire, rulare safe sau test punctual.
6. Daca schimbarea afecteaza workflow-ul, actualizeaza README.md si worklog-ul.

Evita refactorizarile mari. Lucreaza curat, incremental si fara sa inventezi informatii.
```

## Observatie finala

Daca exista conflict intre aceasta regula si conventiile deja folosite in cod, **prefera varianta care pastreaza proiectul functional si compatibil.**
