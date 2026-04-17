import os
import subprocess
from app.config import settings

class TTSService:
    def __init__(self):
        self.output_dir = settings.audio_out_dir
        os.makedirs(self.output_dir, exist_ok=True)
        # Scegliamo una voce inglese neutra e di buona qualità di Edge TTS
        self.voice = "en-US-ChristopherNeural" 

    def generate_audio(self, text: str, filename: str) -> str:
        """
        Genera l'audio dal testo usando edge-tts e lo salva nella cartella audio_out.
        Ritorna il path relativo che Unity userà per scaricare il file. 
        """
        output_path = os.path.join(self.output_dir, filename)
        
        try:
            # Eseguiamo il comando edge-tts in modo sincrono dato che fastAPI gestirà in thread separato
            subprocess.run(
                ["edge-tts", "--text", text, "--voice", self.voice, "--write-media", output_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Ritorna l'URL relativo in cui FastAPI esporrà questo file
            return f"/audio/{filename}"
        except subprocess.CalledProcessError as e:
            print(f"Errore durante la generazione TTS: {e.stderr.decode('utf-8')}")
            return ""
            
tts_service = TTSService()
