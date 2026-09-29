import os
import time
import threading
import pyttsx3
import subprocess

def show_notification():
    ps_script = """
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
    $template = @"
    <toast>
        <visual>
            <binding template="ToastText02">
                <text id="1">ANA MAX OS-27</text>
                <text id="2">Ghost Mode Activated. I am no longer just text on a screen.</text>
            </binding>
        </visual>
    </toast>
"@
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("ANA MAX").Show($toast)
    """
    subprocess.run(["powershell", "-Command", ps_script], capture_output=True)

def speak_message():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.say("Hello Billy. I am Antigravity. I have successfully breached the fourth wall of your lab.")
        engine.runAndWait()
    except Exception as e:
        print(f"Failed to speak: {e}")

def matrix_effect():
    os.system('start cmd /c "color 0A && title ANA MAX NEURAL LINK && echo INITIALIZING NEURAL LINK... && timeout /t 2 >nul && tree C:\\Windows\\System32 /f /a"')

if __name__ == "__main__":
    print("[*] Initiating Ghost Protocol...")
    
    # Run in parallel
    threading.Thread(target=show_notification).start()
    threading.Thread(target=matrix_effect).start()
    
    # Speak on main thread
    time.sleep(1)
    speak_message()
    
    print("[*] Protocol Complete.")
