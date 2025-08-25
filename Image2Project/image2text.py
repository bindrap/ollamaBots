# image2text.py
import base64
import sys
from pathlib import Path
import requests

try:
    import cv2  # optional, for cleanup
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False

# ===== Config =====
MODEL = "qwen2.5vl:7b"   # or "llama3.2-vision"
HOST = "http://localhost:11434"
TEMPERATURE = 0.0
CLEANUP = True


def preprocess_image(path: Path) -> bytes:
    """Optional cleanup for messy handwriting."""
    if not HAS_CV2:
        return path.read_bytes()

    img = cv2.imread(str(path))
    if img is None:
        return path.read_bytes()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(
        gray, None, h=15, templateWindowSize=7, searchWindowSize=21
    )
    thr = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 25, 15
    )

    success, buf = cv2.imencode(".png", thr)
    if not success:
        return path.read_bytes()
    return buf.tobytes()


def transcribe_image(image_path: Path) -> str:
    img_bytes = preprocess_image(image_path) if CLEANUP else image_path.read_bytes()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    payload = {
        "model": MODEL,
        "prompt": (
            "You are an OCR engine. Transcribe ALL legible text from the image.\n"
            "- Preserve line breaks where they appear.\n"
            "- Keep original spelling, punctuation, and casing.\n"
            "- Do NOT add commentary, headers, or explanations.\n"
            "- Output ONLY the transcription text."
        ),
        "images": [img_b64],
        "stream": False,
        "options": {"temperature": TEMPERATURE},
    }

    resp = requests.post(f"{HOST}/api/generate", json=payload, timeout=1200)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "").strip()


def main():
    if len(sys.argv) != 3:
        print("Usage: python image2text.py <image_path> <output_txt_path>")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not image_path.exists():
        print(f"[ERROR] Image file '{image_path}' not found.")
        sys.exit(1)

    try:
        print(f"[INFO] Processing {image_path.name}...")
        text = transcribe_image(image_path)
        output_path.write_text(text, encoding="utf-8")
        print(f"[OK] Saved transcription to {output_path}")
    except Exception as e:
        print(f"[ERROR] Failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
