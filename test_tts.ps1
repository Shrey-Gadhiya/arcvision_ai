
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('Microsoft David Desktop')
$s.Rate = 0
$s.SetOutputToWaveFile('test_voice.wav')
$s.Speak('ARC VISION. Autonomous tactical border surveillance for IBM BOB 2.0 Hackathon.')
$s.Dispose()
