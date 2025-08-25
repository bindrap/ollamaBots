# orchestrator.py
import subprocess
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        print("Usage: python orchestrator.py <image_file> <output_markdown>")
        sys.exit(1)

    image_file = Path(sys.argv[1])
    output_md = Path(sys.argv[2])

    if not image_file.exists():
        print(f"[ERROR] Image file {image_file} not found.")
        sys.exit(1)

    # Intermediate text file
    temp_txt = image_file.stem + "_transcribed.txt"

    # Step 1: Run OCR (image2text.py)
    print(f"[INFO] Running OCR on {image_file.name}...")
    result = subprocess.run(
        [sys.executable, "image2text.py", str(image_file), temp_txt],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("[ERROR] OCR failed:\n", result.stderr.strip())
        sys.exit(1)
    print("[OK] OCR complete")

    # Step 2: Analyze text into project plan (text2project.py)
    print("[INFO] Creating project plan...")
    result = subprocess.run(
        [sys.executable, "text2project.py", temp_txt, str(output_md)],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("[ERROR] Project analysis failed:\n", result.stderr.strip())
        sys.exit(1)

    print(f"[OK] Project plan saved to {output_md}")


if __name__ == "__main__":
    main()
