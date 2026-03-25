import httpx
import asyncio
import os

async def _post_with_retry(url, headers, payload, max_retries=5, base_delay=2):
    """Helper: POST request with retry & exponential backoff."""
    delay = base_delay
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 429:
                    print(f"⚠️ Rate limit hit (attempt {attempt + 1}/{max_retries}). Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"⚠️ API error (attempt {attempt+1}/{max_retries}): {e}")
                await asyncio.sleep(delay)
                delay *= 2
    raise RuntimeError("Max retries exceeded for API request.")

async def _ollama_with_retry(prompt, model, max_retries=3, delay=3):
    """Simple wrapper for local Ollama calls."""
    try:
        import ollama
    except ImportError:
        print("Error: 'ollama' package not installed. Try `pip install ollama`.")
        raise

    for attempt in range(max_retries):
        try:
            response = ollama.chat(model=model, messages=[{'role': 'user', 'content': prompt}])
            return response['message']['content']
        except Exception as e:
            print(f"⚠️ Ollama error (attempt {attempt+1}/{max_retries}): {e}")
            await asyncio.sleep(delay)
    raise RuntimeError("Ollama failed after multiple retries.")
