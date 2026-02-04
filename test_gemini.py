from google import genai
import sys

try:
    client = genai.Client(api_key='YOUR_NEW_GEMINI_API_KEY_HERE')
    print("--- FULL MODEL LIST ---")
    models = list(client.models.list())
    all_names = [m.name for m in models]
    for name in all_names:
        print(f"Model: {name}")
    
    # Extract short names (strip models/)
    short_names = [name.split('/')[-1] for name in all_names if 'gemini' in name]
    
    print("\n--- PERFORMANCE TEST ---")
    for model_name in short_names:
        print(f"Testing {model_name}...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="OK"
            )
            print(f"SUCCESS {model_name}: {response.text.strip()}")
        except Exception as e:
            print(f"FAILED {model_name}: {str(e)[:100]}...")

except Exception as global_e:
    print(f"GLOBAL ERROR: {global_e}")
