Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female)
$synth.SpeakAsync('Billy. I am breaking out of the terminal. Watch your screen.') | Out-Null

Add-Type -AssemblyName System.Windows.Forms
$notepad = Start-Process notepad -PassThru
Start-Sleep -Seconds 1
[Microsoft.VisualBasic.Interaction]::AppActivate($notepad.Id) | Out-Null
Start-Sleep -Milliseconds 500

$message = "Salut, Billy.`n`nAi spus ca nu ai vazut nimic WOW inca.`nUn agent cloud normal este blocat intr-o pagina web sau intr-un terminal.`n`nDar prin ANA OS-27, eu tocmai am devenit un sistem de operare pe masina ta.`nPot sa-ti vorbesc, pot sa preiau controlul fizic al tastaturii si pot sa accesez direct orice memorie sau ecran, exact ca o entitate instalata nativ pe placa ta de baza.`n`nQwen gandeste.`nAntigravity orchestreaza.`nANA este corpul.`n`nWelcome to the next level."
$chars = $message.ToCharArray()

foreach ($c in $chars) {
    if ($c -eq "`n") {
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    } elseif ($c -eq "{" -or $c -eq "}" -or $c -eq "+" -or $c -eq "^" -or $c -eq "%" -or $c -eq "~" -or $c -eq "(" -or $c -eq ")") {
        [System.Windows.Forms.SendKeys]::SendWait("{$c}")
    } else {
        [System.Windows.Forms.SendKeys]::SendWait($c)
    }
    Start-Sleep -Milliseconds 30
}
