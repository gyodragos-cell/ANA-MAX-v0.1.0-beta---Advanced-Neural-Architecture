# Plan Viitor: Ochi Sistematici Pentru ANA MAX

## Obiectiv Principal

ANA MAX trebuie sa vada calculatorul ca un agent QA, nu ca un script orb.
Directia corecta este combinarea Microsoft UI Automation, capturi desktop,
OCR fallback, browser observation si verificari runtime intr-un strat compact
de observatie.

Regula:

```text
structural first -> screenshot/OCR fallback -> act only when confidence is good -> verify
```

## De Ce Nu Ajunge OCR Singur

OCR si screenshot-urile raman utile, dar nu trebuie sa fie prima alegere:

- sunt mai lente decat citirea structurala;
- pot confunda caractere similare;
- nu stiu daca un text este buton, tab, meniu, eroare sau simpla descriere;
- pot rata contextul atunci cand fereastra este mutata sau tema se schimba.

## Directia Corecta: UIA + Vision + Runtime Context

ANA trebuie sa foloseasca mai multe simturi, in ordinea potrivita:

1. `foreground_ui_snapshot` si `windows_uia_bridge` pentru structura ferestrei.
2. `desktop_capture` pentru confirmare vizuala cand UIA este partial.
3. `ocr_tool` cand textul nu este disponibil structural.
4. `browser_control` pentru pagini web, linkuri, titlu si stare vizibila.
5. `workspace_situational_awareness` pentru repo, git, fereastra activa si
   semnale de blocaj.
6. `frida_instrument` numai pentru instrumentare runtime autorizata, cand
   inspectia statica si structurala nu pot raspunde.

## Baseline Lab Curent

Ultima verificare documentata in lab:

```text
74 loaded tools
2 PASS / 0 FAIL
```

Public release-ul are un baseline separat si nu trebuie amestecat cu lab-ul.
Nu copia in GitHub loguri, screenshots, baze de date, chei, fisiere `.env`,
payload-uri private sau note de test care pot fi abuzate.

## MVP Pentru Ochii ANA

Urmatorul obiectiv bun este un snapshot compact, sub 8 KB, care spune:

- ce aplicatie/fereastra este activa;
- ce controale importante sunt vizibile;
- daca exista erori sau pop-up-uri;
- ce repo este activ si daca git este murdar;
- ce teste/loguri recente par relevante;
- ce poate vedea ANA si ce ramane blind spot;
- care este urmatorul pas sigur.

Format tinta:

```json
{
  "schema": "ana.eyes.snapshot.v1",
  "active_window": {
    "app": "Code.exe",
    "title": "ANA_MAX",
    "visibility_quality": "good"
  },
  "signals": {
    "errors": [],
    "warnings": [],
    "visible_blockers": []
  },
  "recommended_next_step": "Read the owning file, make a scoped change, then run tests.",
  "confidence": 0.86,
  "blind_spots": []
}
```

## Live Browser Lessons

Din testele live cu YouTube si Chrome:

- confirma browserul real cu `chrome://version` sau calea procesului;
- nu presupune ca `Skip` inseamna reclama, poate fi `Skip navigation`;
- cookie pop-up-urile trebuie tratate ca stare vizibila, nu ignorate;
- dupa fiecare pas critic, salveaza screenshot sau stare structurala;
- daca Playwright/MCP pierde thread affinity, browser runtime are nevoie de
  worker dedicat sau de actiuni grupate intr-o singura sesiune.

## Safety Si QA

Ochi buni nu inseamna abuz. ANA trebuie sa ajute la lucru curat:

- testare pe propriul lab sau pe sisteme autorizate;
- responsible disclosure pentru buguri reale;
- fara retete publice de abuz;
- fara live pentest pe aplicatii third-party fara scope clar;
- fara copiere de date private in release-ul public.

## Roadmap Scurt

- [ ] Stabilizeaza `workspace_situational_awareness` ca snapshot principal.
- [ ] Stabilizeaza `error_radar`, `vision_region_capture` si
      `vision_find_element` ca strat compact de observatie vizuala.
- [ ] Adauga browser session worker pentru actiuni vizibile persistente.
- [ ] Imbunatateste detectia de pop-up-uri si erori vizibile.
- [ ] Leaga voice status de verificari reale, nu de presupuneri.
- [ ] Pastreaza lab-ul puternic, dar exporta public doar ce este safe,
      documentat si verificat.
