import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty('voices')

for index, voice in enumerate(voices):
    print(f"[{index}] ID: {voice.id}")
    print(f"    Nom: {voice.name}")
    print(f"    Langue: {voice.languages}")
    print("-" * 30)