using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class TouchScript : MonoBehaviour
{
    // Start is called before the first frame update
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        
    }
    public AudioSource audioIntro;
    public AudioSource audioLoop; // Trascina qui il componente ConvaiNPC

    private void OnTriggerEnter(Collider other)
    {
        // Se l'oggetto che tocca l'avatar ha il tag "Player" o "Hand"
        if (other.CompareTag("Player") || other.gameObject.name.Contains("Hand"))
        {
            StartCoroutine(SequenzaTocco());
        }
    }

    IEnumerator SequenzaTocco()
    {
        // 1. Parte l'intro
        audioIntro.Play();
        
        // 2. Aspetta che l'intro finisca
        yield return new WaitForSeconds(audioIntro.clip.length);
        
        // 3. Parte il loop
        audioLoop.Play();
        
        // 4. Attiva Convai (accende il componente che era spento)
        
    }

    private void OnTriggerExit(Collider other)
    {
        // Quando smetti di toccarlo, spegne tutto
        if (other.CompareTag("Player") || other.gameObject.name.Contains("Hand"))
        {
            audioIntro.Stop();
            audioLoop.Stop();
        
        }
    }
}
