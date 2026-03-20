import subprocess

def speak(text: str) -> None:
    print(f"Vasya: {text}")
    subprocess.run(["say", text], check=False)