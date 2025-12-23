from google import genai

# INCOLLA QUI LA TUA API KEY NUOVA
API_KEY = "AIzaSyDcRMGwzpIZzeA1G_7s_dWvaT3NkYmDgj0"

client = genai.Client(api_key=API_KEY)

print("🔍 Cerco i modelli disponibili...\n")

try:
    # Prende la lista e stampa il nome di ogni modello trovato
    for m in client.models.list():
        print(f" -> {m.name}")
            
except Exception as e:
    print(f"❌ Errore: {e}")