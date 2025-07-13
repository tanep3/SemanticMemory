import requests

def summarize_text(text, system_prompt="以下のテキストを日本語で簡潔に要約してください。", model="mistral:latest", url="http://localhost:11434"):
    """
    Ollama APIで要約する
    """
    prompt = f"system: {system_prompt}\n\n{text}"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    res = requests.post(
        f"{url}/api/generate",
        json=payload,
        timeout=60
    )
    res.raise_for_status()
    data = res.json()
    summary = data.get("response", "").strip()
    return summary
