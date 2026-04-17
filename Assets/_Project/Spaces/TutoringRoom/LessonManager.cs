using UnityEngine;
using TMPro;
using UnityEngine.Networking;
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;

public class LessonManager : MonoBehaviour
{
    [Header("UI Elements")]
    public TextMeshProUGUI dialogText;

    [Header("Impostazioni Audio")]
    public AudioSource audioSource;
    private string pcMicDeviceName;
    private AudioClip recordedClip;
    private bool isRecording = false;

    private void Start()
    {
        // Unity rileva tutti i microfoni collegati.
        // Di solito il primo (indice 0) è quello predefinito di Windows/Mac.
        // Se hai problemi, potremo stampare l'elenco e forzare il nome esatto.
        if (Microphone.devices.Length > 0)
        {
            pcMicDeviceName = Microphone.devices[0];
            Debug.Log("Microfono selezionato: " + pcMicDeviceName);
        }
        else
        {
            Debug.LogError("Nessun microfono rilevato!");
        }
    }



    public void StartRecording()
    {
        if (pcMicDeviceName == null) return;

        dialogText.text = "In ascolto... Parla ora!";
        isRecording = true;
        
        // Inizia a registrare. Parametri: nome del device, non in loop, durata max 60 secondi, 44100 Hz (qualità standard)
        recordedClip = Microphone.Start(pcMicDeviceName, false, 60, 44100);
        Debug.Log("Registrazione avviata...");
    }

public void StopRecordingAndSend()
    {
        if (isRecording)
        {
            int position = Microphone.GetPosition(pcMicDeviceName);
            Microphone.End(pcMicDeviceName);
            isRecording = false;

            dialogText.text = "Elaborazione audio...";
            
            // Taglia la clip alla lunghezza esatta del parlato e invia
            AudioClip trimmedClip = TrimAudioClip(recordedClip, position);
            StartCoroutine(SendTurnAudio(trimmedClip));
        }
    }

    private IEnumerator SendTurnAudio(AudioClip clip)
    {
        dialogText.text = "Invio audio al professore...";

        // 1. Convertiamo l'AudioClip in Byte Array (formato WAV)
        byte[] wavBytes = ConvertClipToWav(clip);

        // 2. Prepariamo il form multipart per inviare il file audio
        List<IMultipartFormSection> formData = new List<IMultipartFormSection>
        {
            new MultipartFormFileSection("audio_file", wavBytes, "studente_audio.wav", "audio/wav")
        };

        // 3. Facciamo la chiamata POST al backend
        UnityWebRequest request = UnityWebRequest.Post(backendUrl + "/turn", formData);
        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            ProcessBackendResponse(request.downloadHandler.text);
        }
        else
        {
            dialogText.text = "Errore di connessione: " + request.error;
            Debug.LogError("Errore API: " + request.error);
        }
    }
private AudioClip TrimAudioClip(AudioClip original, int lastPosition)
    {
        if (lastPosition == 0) return original;
        float[] data = new float[lastPosition * original.channels];
        original.GetData(data, 0);
        AudioClip trimmed = AudioClip.Create("Trimmed", lastPosition, original.channels, original.frequency, false);
        trimmed.SetData(data, 0);
        return trimmed;
    }

    private byte[] ConvertClipToWav(AudioClip clip)
    {
        MemoryStream stream = new MemoryStream();
        BinaryWriter writer = new BinaryWriter(stream);

        float[] samples = new float[clip.samples * clip.channels];
        clip.GetData(samples, 0);

        Int16[] intData = new Int16[samples.Length];
        byte[] bytesData = new byte[samples.Length * 2];
        const int rescaleFactor = 32767; // Converte float a Int16

        for (int i = 0; i < samples.Length; i++)
        {
            intData[i] = (short)(samples[i] * rescaleFactor);
            byte[] byteArr = System.BitConverter.GetBytes(intData[i]);
            byteArr.CopyTo(bytesData, i * 2);
        }

        // Intestazione standard WAV (44 bytes)
        writer.Write(System.Text.Encoding.UTF8.GetBytes("RIFF"));
        writer.Write(36 + bytesData.Length);
        writer.Write(System.Text.Encoding.UTF8.GetBytes("WAVE"));
        writer.Write(System.Text.Encoding.UTF8.GetBytes("fmt "));
        writer.Write(16);
        writer.Write((short)1); // PCM
        writer.Write((short)clip.channels);
        writer.Write(clip.frequency);
        writer.Write(clip.frequency * clip.channels * 2);
        writer.Write((short)(clip.channels * 2));
        writer.Write((short)16); // Bits per sample
        writer.Write(System.Text.Encoding.UTF8.GetBytes("data"));
        writer.Write(bytesData.Length);

        // Scrittura dei dati audio effettivi
        writer.Write(bytesData);
        writer.Close();

        return stream.ToArray();
    }

    public void OnStartLessonClicked()
    {
        StartCoroutine(GetInitialLessonData());
    }

    private IEnumerator GetInitialLessonData()
    {
        dialogText.text = "Inizializzazione lezione...";
        
        // Assumendo che il tuo endpoint per iniziare sia /start
        // Se nel tuo test_api.py l'endpoint è /exam/start con parametri, aggiornalo qui se necessario
        using (UnityWebRequest request = UnityWebRequest.Get(backendUrl + "/exam/start")) // o /start a seconda del backend
        {
            yield return request.SendWebRequest();

            if (request.result == UnityWebRequest.Result.Success)
            {
                ProcessBackendResponse(request.downloadHandler.text);
            }
            else
            {
                dialogText.text = "Errore Start: " + request.error;
            }
        }
    }

    private void ProcessBackendResponse(string jsonResponse)
    {
        // Deserializziamo il JSON
        LessonSession session = Newtonsoft.Json.JsonConvert.DeserializeObject<LessonSession>(jsonResponse);
        
        // Troviamo l'ultimo turno che non sia dello studente (quindi Professore o Evaluation)
        Turn lastTurn = session.turns.LastOrDefault(t => t.role == "professor" || t.role == "evaluation");

        if (lastTurn != null)
        {
            // 1. Mostriamo il testo sul Canvas
            dialogText.text = lastTurn.text;

            // 2. Se c'è un file audio, lo scarichiamo e lo riproduciamo
            // Nota: Assicurati che il backend ti passi un URL completo o un path relativo
            if (!string.IsNullOrEmpty(lastTurn.audio_file))
            {
                string audioUrl = lastTurn.audio_file.StartsWith("http") ? 
                                  lastTurn.audio_file : 
                                  backendUrl + "/" + lastTurn.audio_file;
                
                StartCoroutine(DownloadAndPlayAudio(audioUrl));
            }
        }
    }

    private IEnumerator DownloadAndPlayAudio(string url)
    {
        using (UnityWebRequest www = UnityWebRequestMultimedia.GetAudioClip(url, AudioType.MPEG)) // Usiamo MPEG per riprodurre file MP3
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                AudioClip clip = DownloadHandlerAudioClip.GetContent(www);
                audioSource.clip = clip;
                audioSource.Play();
            }
            else
            {
                Debug.LogError("Errore download audio: " + www.error);
            }
        }
    }

    public void OnEndLessonClicked()
    {
        StartCoroutine(GetFinalFeedback());
    }

    private IEnumerator GetFinalFeedback()
    {
        dialogText.text = "Generazione feedback finale...";

        // Se nel tuo backend l'url è /exam/end, ricordati di aggiornarlo. Metto /end come da snippet.
        using (UnityWebRequest request = UnityWebRequest.Get(backendUrl + "/end"))
        {
            yield return request.SendWebRequest();

            if (request.result == UnityWebRequest.Result.Success)
            {
                LessonSession session = Newtonsoft.Json.JsonConvert.DeserializeObject<LessonSession>(request.downloadHandler.text);
                
                // Cerchiamo il turno di tipo 'evaluation'
                var evalTurn = session.turns.LastOrDefault(t => t.role == "evaluation");
                if (evalTurn != null)
                {
                    // Mostriamo il feedback complessivo (overall)
                    dialogText.text = $"<b>RISULTATO FINALE</b>\n\n{evalTurn.feedback.overall}";
                    
                    // Opzionale: riproduci audio del feedback se presente
                    if (!string.IsNullOrEmpty(evalTurn.audio_file)) 
                        StartCoroutine(DownloadAndPlayAudio(backendUrl + "/" + evalTurn.audio_file));
                }
            }
        }
    }


    [System.Serializable]
    public class LessonSession {
        public string session_id;
        public string status;
        public System.Collections.Generic.List<Turn> turns;
    }

    [System.Serializable]
    public class Turn {
        public string role;
        public string text;
        public string audio_file;
        public EvaluationFeedback feedback;
    }

    [System.Serializable]
    public class EvaluationFeedback {
        public string overall;
    }

[Header("Impostazioni API")]
    public string backendUrl = "http://localhost:5001"; // Sostituisci con il tuo URL

}