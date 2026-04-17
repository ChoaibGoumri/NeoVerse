import requests
import json
import os

BASE_URL = "http://localhost:5001"
# Usiamo il file audio reale presente nella cartella per un test veritiero
AUDIO_TEST_FILE = "test.aiff"

if not os.path.exists(AUDIO_TEST_FILE):
    # Se proprio non c'è, ne creiamo uno fittizio (ma questo ci fa falire il Whisper)
    with open(AUDIO_TEST_FILE, "wb") as f:
        f.write(b"dummy audio data")

def test_health():
    print("Test 1: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}\n")
        assert response.status_code == 200
        return True
    except Exception as e:
        print(f"Errore: {e}\n")
        return False

def test_start_exam_invalid_subject():
    # Deprecated since subject is now hardcoded in the backend. Skipping.
    return True

def test_start_exam_valid():
    print("Test 3: Start Exam (Valido)")
    payload = {
        "user_id": "test_user_01"
    }
    try:
        response = requests.post(f"{BASE_URL}/exam/start", json=payload)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        if response.status_code != 200:
            print(f"Errore dal Server: {data}")
            return None
        print(f"Session ID: {data.get('session_id')}")
        print(f"Intro: {data.get('question_text', '')[:100]}...\n")
        return data.get('session_id')
    except Exception as e:
        print(f"Errore eccezione: {e}\n")
        return None

def test_answer_audio(session_id):
    if not session_id:
        print("Skipping Test 4 (no session_id)")
        return False
        
    print("Test 4: Answer Audio (Valido)")
    data = {
        "user_id": "test_user_01",
        "session_id": session_id
    }
    try:
        with open(AUDIO_TEST_FILE, "rb") as f:
            files = {"audio": (AUDIO_TEST_FILE, f, "audio/aiff")}
            # Aggiungiamo un timeout alto perchè Gemini e Whisper possono impiegare tempo
            response = requests.post(f"{BASE_URL}/exam/answer-audio", data=data, files=files, timeout=120)
        
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)[:300]}...\n")
        except:
            print(f"Response (no JSON): {response.text[:300]}...\n")
            
        assert response.status_code == 200
        return True
    except Exception as e:
        print(f"Errore: {e}\n")
        return False

def test_end_exam(session_id):
    if not session_id:
        print("Skipping Test 5 (no session_id)")
        return False
        
    print("Test 5: End Exam")
    params = {
        "user_id": "test_user_01",
        "session_id": session_id
    }
    try:
        response = requests.post(f"{BASE_URL}/exam/end", params=params, timeout=120)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")
        assert response.status_code == 200
        return True
    except Exception as e:
        print(f"Errore: {e}\n")
        return False

if __name__ == "__main__":
    print("--- INIZIO TEST API ---")
    print("Assicurati che il server sia in esecuzione su http://localhost:5001\n")
    
    test_health()
    test_start_exam_invalid_subject()
    
    session_id = test_start_exam_valid()
    
    # Questo test manderà un audio falso ("dummy audio data"), 
    # quindi Whisper trascriverà qualcosa di vuoto o strano, 
    # ma serve a testare che l'endpoint completi il giro correttamente.
    if session_id:
        test_answer_audio(session_id)
        test_end_exam(session_id)
        
    print("--- FINE TEST API ---")
