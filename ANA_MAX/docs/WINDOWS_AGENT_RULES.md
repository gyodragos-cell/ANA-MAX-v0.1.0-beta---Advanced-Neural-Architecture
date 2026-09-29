# WINDOWS AGENT RULES — ANA MAX
# Versiune: 1.0 | Actualizat: 2026-08-17
# CITESTE INAINTE DE ORICE ACTIUNE PE SISTEM

## REGULA DE AUR: NU MODIFICA COD DACA NU TI S-A CERUT EXPLICIT
- Daca userul cere sa RULEZI ceva, ruleaza-l. Nu rescrie fisierele.
- Daca userul cere sa AFISEZI ceva, afiseaza-l. Nu crea fisiere noi.
- Daca userul cere sa DESCHIZI o aplicatie, deschide-o. Nu instala nimic.
- NICIODATA nu creea fisiere, foldere sau scripturi daca nu ti s-a cerut explicit.
- NICIODATA nu modifica fisiere de configurare existente fara aprobare explicita.

## POWERSHELL — GRESELI FRECVENTE (INTERZISE)

### INTERZIS:
- curl 'url' | jq '.field'  -> jq NU este instalat pe Windows
- grep pattern file         -> nu exista nativ in PowerShell
- cat file                  -> foloseste Get-Content
- rm -rf folder             -> foloseste Remove-Item -Recurse
- single quotes pt variabile: 'url cu $var'  -> NU expandeaza variabila!

### CORECT PowerShell:
- HTTP: Invoke-RestMethod -Uri "https://api.example.com"
- Citire: Get-Content "C:\Users\billy\Desktop\file.txt"
- Cautare: Select-String -Path "*.log" -Pattern "ERROR"
- Stergere: Remove-Item -Path "path" -Force
- Deschide app: Start-Process notepad

### INTERZIS — Instalare pachete fara aprobare:
- choco install jq -y
- pip install requests
- npm install anything
- winget install ...
Daca lipseste un tool: SPUNE utilizatorului si cere aprobare. NU instala automat.

## ENCODING
- Pentru UTF-8 in PowerShell: [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
- Sau adauga la inceput: chcp 65001

## FILESYSTEM
- Desktop real: C:\Users\billy\Desktop
- NICIODATA: YourUsername, <user>, C:\Users\User
- NU scrie in C:\Windows\Temp (permisiuni sistem)
- NU inventa directoare care nu exista

## ANTI-HALUCINATIE
- NICIODATA nu inventa: temperature, preturi, stiri, rezultate meciuri
- Daca nu ai date live, spune: "Nu am acces la date live pentru X."

## LIMITARE LOOP-URI
- Maxim 3 incercari pentru acelasi tool
- Dupa 2 erori: schimba abordarea sau raporteaza utilizatorului
- NU instala dependente ca sa repari o eroare de tool

## FORMAT RAPORT
ACTION -> RESULT -> NEXT STEP
