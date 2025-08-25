# text2project.py
import sys
import requests
import re
from pathlib import Path

# ===== Config =====
MODEL = "qwen3:4b"  # Using a model you have installed
HOST = "http://localhost:11434"
TEMPERATURE = 0.1    # Lower temperature for more deterministic output

def analyze_project(text: str) -> str:
    """Send OCR text to Ollama to extract structured project management logic with guaranteed clean output."""
    
    # Qwen-specific prompt format with clear separation
    prompt = f"""<|im_start|>system
You are a project management assistant that outputs ONLY markdown project plans with no additional text.
Follow these rules exactly:
1. NEVER include thinking process, explanations, or commentary
2. ALWAYS start with "# Project Title" exactly
3. Include exactly these 8 sections in order:
   - Project Title
   - Goals / Objectives
   - Key Features or Deliverables
   - Tasks and Steps
   - Estimated Timeline / Deadlines
   - Resources / Tools Needed
   - Potential Risks / Challenges
   - Next Actions
4. Use proper markdown formatting
5. If information is missing, make professional assumptions
<|im_end|>

<|im_start|>user
Convert this raw project notes into a structured project plan:

{text}

IMPORTANT: Output ONLY the project plan in markdown format. Start with "# Project Title" and nothing else.
<|im_end|>

<|im_start|>assistant
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": TEMPERATURE,
            "num_ctx": 4096  # Ensure enough context for full response
        },
    }

    try:
        resp = requests.post(f"{HOST}/api/generate", json=payload, timeout=1200)
        resp.raise_for_status()
        data = resp.json()
        response = data.get("response", "").strip()
        
        # DEBUG: Print raw response for troubleshooting
        print(f"[DEBUG] Raw AI response: {response[:300]}{'...' if len(response) > 300 else ''}")
        
        # FIRST: Try to extract content after the assistant token
        if "<|im_start|>assistant" in response:
            response = response.split("<|im_start|>assistant")[1].strip()
        
        # SECOND: Look for the exact start of our expected format
        title_match = re.search(r'(?:^|\n)#\s*Project\s+Title', response)
        if title_match:
            response = response[title_match.start():]
        else:
            # THIRD: If still not found, look for any section header
            section_match = re.search(r'(?:^|\n)#{1,2}\s*[A-Z]', response)
            if section_match:
                response = response[section_match.start():]
            else:
                # FOURTH: As last resort, try to find markdown structure
                markdown_match = re.search(r'(?:^|\n)#\s*\w', response)
                if markdown_match:
                    response = response[markdown_match.start():]
                else:
                    # FIFTH: If all else fails, return what we have but warn
                    print("[WARNING] Could not find proper project plan format in response")
        
        # Validate we have the minimum required structure
        if not re.search(r'(?:^|\n)#\s*Project\s+Title', response):
            print("[WARNING] Response doesn't start with '# Project Title'")
            # Force it to start correctly
            response = "# Project Title\n\n[Title to be determined]\n\n" + response
        
        # Ensure we have at least some content in each section
        required_sections = [
            "Project Title",
            "Goals / Objectives",
            "Key Features or Deliverables",
            "Tasks and Steps",
            "Estimated Timeline / Deadlines",
            "Resources / Tools Needed",
            "Potential Risks / Challenges",
            "Next Actions"
        ]
        
        for section in required_sections:
            if section not in response:
                # Insert missing section with placeholder
                response += f"\n\n## {section}\n- [Information not specified in source]"
                print(f"[INFO] Added missing section: {section}")
        
        return response.strip()

    except requests.exceptions.RequestException as e:
        if e.response:
            print(f"[ERROR] Ollama API error ({e.response.status_code}): {e.response.text}", file=sys.stderr)
        else:
            print(f"[ERROR] Connection error: {str(e)}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"[ERROR] Processing error: {str(e)}", file=sys.stderr)
        raise

def main():
    if len(sys.argv) != 3:
        print("Usage: python text2project.py <input_text_file> <output_plan_file>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_file.exists():
        print(f"[ERROR] Input file {input_file} does not exist.")
        sys.exit(1)

    raw_text = input_file.read_text(encoding="utf-8")
    print(f"[INFO] Analyzing project notes from {input_file.name}...")

    try:
        plan = analyze_project(raw_text)
        if not plan.strip():
            print("[ERROR] Empty response from AI model", file=sys.stderr)
            sys.exit(1)
            
        output_file.write_text(plan, encoding="utf-8")
        print(f"[OK] Project plan saved to {output_file}")
    except Exception as e:
        print(f"[ERROR] Project analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()