#!/usr/bin/env python3
"""
NoteBot - AI-Powered Note Enhancement Tool

Converts raw text notes into beautifully formatted Markdown with AI assistance.
Can process single files or entire folders of notes.

Usage:
  # Process a single note
  python noteBot.py "path/to/note.txt" "path/to/output.md"
  
  # Process all notes in default folders
  python noteBot.py
  
  # Process all notes in a specific folder
  python noteBot.py "path/to/notes_folder"
"""

import subprocess
import os
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
import sys
import re

# === Global Configs ===
OLLAMA_PATH = r"C:\Users\bindrap\AppData\Local\Programs\Ollama\ollama.exe"
DEFAULT_INPUT_FOLDER = Path(r"C:\Users\bindrap\Downloads\noteBot\Notes")
DEFAULT_OUTPUT_FOLDER = DEFAULT_INPUT_FOLDER / "Markdown Outputs"
MODEL_NAME = "qwen3:4b"   # 👈 change model name here globally

# Model quality reference (higher = better quality but slower)
MODEL_QUALITY = {
    "qwen3:4b": 8,
    "qwen3:8b": 9,
    "mistral:latest": 7,
    "gemma3:1b": 5
}

# Setup logging
def setup_logging(input_path):
    """Configure logging based on input path to keep logs organized"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(input_path).parent / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"{timestamp}_notebot.log"
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return log_file

def ensure_model():
    """Check if a model exists locally; if not, pull it."""
    logging.info(f"Checking if model '{MODEL_NAME}' exists locally...")
    print(f"🔍 Checking if model '{MODEL_NAME}' exists locally...")
    try:
        result = subprocess.run([OLLAMA_PATH, "list"], capture_output=True, text=True, check=True)
        
        # Parse model list - handle different Ollama output formats
        models = []
        for line in result.stdout.strip().splitlines()[1:]:  # Skip header
            parts = line.split()
            if parts:
                # Handle both "NAME ID SIZE MODIFIED" and "NAME SHORT_ID SIZE MODIFIED" formats
                if len(parts) >= 1:
                    models.append(parts[0])
        
        if MODEL_NAME not in models:
            logging.info(f"Model '{MODEL_NAME}' not found. Downloading...")
            print(f"📥 Model '{MODEL_NAME}' not found. Downloading...")
            pull_result = subprocess.run(
                [OLLAMA_PATH, "pull", MODEL_NAME], 
                capture_output=True, 
                text=True,
                check=True
            )
            
            # Check if pull was successful
            if "pulling manifest" in pull_result.stdout.lower() or "pulled" in pull_result.stdout.lower():
                logging.info(f"Model '{MODEL_NAME}' downloaded successfully.")
                print(f"✅ Model '{MODEL_NAME}' downloaded successfully.")
            else:
                logging.error(f"Model download may have failed: {pull_result.stdout}")
                print(f"⚠️ Model download may have incomplete: Check logs")
                return False
        else:
            logging.info(f"Model '{MODEL_NAME}' is already available.")
            print(f"✅ Model '{MODEL_NAME}' is already available.")
        
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"Error checking/downloading model: {e}\n{e.stderr}"
        logging.error(error_msg)
        print(f"❌ Error checking/downloading model: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error checking model: {str(e)}")
        print(f"❌ Unexpected error checking model: {str(e)}")
        return False

def ollama_query(prompt: str, timeout: int = 1200) -> str:
    """Send a prompt to Ollama and return the response with enhanced error handling."""
    logging.info(f"Querying model '{MODEL_NAME}'...")
    print(f"🤖 Querying model '{MODEL_NAME}' (quality: {MODEL_QUALITY.get(MODEL_NAME, 'N/A')}/10)...")
    start_time = time.time()
    
    try:
        # Use API directly for more reliable response parsing
        import requests
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        
        elapsed = time.time() - start_time
        logging.info(f"Model responded in {elapsed:.2f}s")
        print(f"✅ Model responded in {elapsed:.2f}s")
        return result.get("response", "").strip()
        
    except requests.exceptions.RequestException as e:
        # Fallback to CLI if API fails
        logging.warning(f"API failed ({str(e)}), trying CLI method...")
        print(f"⚠️ API failed, trying CLI method...")
        
        try:
            result = subprocess.run(
                [OLLAMA_PATH, "run", MODEL_NAME, "--hidethinking"],
                input=prompt.encode(),
                capture_output=True,
                timeout=timeout
            )
            result.check_returncode()
            elapsed = time.time() - start_time
            logging.info(f"Model responded via CLI in {elapsed:.2f}s")
            print(f"✅ Model responded via CLI in {elapsed:.2f}s")
            return result.stdout.decode().strip()
        except Exception as cli_e:
            logging.error(f"CLI method also failed: {str(cli_e)}")
            print(f"❌ Both API and CLI methods failed")
            return "⚠️ Model query failed with all methods."
    except Exception as e:
        logging.error(f"Unexpected error during model query: {str(e)}")
        print(f"❌ Unexpected error: {str(e)}")
        return f"⚠️ Unexpected error: {str(e)}"

def build_prompt(notes: str) -> str:
    """Build a prompt that forces clean, direct Markdown output without any thinking text."""
    
    # Qwen-specific formatting for best results
    return f"""<|im_start|>system
You are a professional note formatter with expertise in technical documentation.
Your ONLY task is to convert raw notes into clean, well-structured Markdown.
Follow these rules EXACTLY:
- NEVER include thinking text, explanations, or commentary
- ALWAYS start with the content immediately - no greetings or introductions
- Output ONLY valid Markdown with no extra text before or after
- Use proper Markdown syntax (headers, lists, code blocks when appropriate)
- Structure content logically with clear sections
- Include a brief summary at the top if appropriate
- Add a "Next Steps" section with actionable items
- Fix spelling/grammar but preserve the original meaning
- If information is unclear, make minimal professional assumptions
<|im_end|>

<|im_start|>user
Enhance these raw notes into professional Markdown format:

{notes}

IMPORTANT: Output ONLY the enhanced notes in Markdown format. Begin with content immediately.
<|im_end|>

<|im_start|>assistant
"""

def clean_model_output(output: str) -> str:
    """
    Clean the model output to ensure it's pure Markdown with no AI thinking text.
    Handles multiple potential issue patterns.
    """
    # Remove common thinking patterns
    patterns = [
        r'(?i)thinking.*?:.*?(?=\n[#=])',  # "Thinking: ..." before headers
        r'(?i)thinking.*?$',
        r'(?i)here.*?is.*?the.*?enhanced.*?version',
        r'(?i)i will now.*?enhance.*?these.*?notes',
        r'(?i)as requested.*?converting',
        r'(?i)enhanced notes:',
        r'(?i)output:',
        r'<\|im_start\|>.*?<\|im_end\|>',
        r'```markdown.*?```',
        r'```.*?```'  # Any code blocks around the content
    ]
    
    cleaned = output
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove any leading/trailing whitespace and non-Markdown content
    cleaned = cleaned.strip()
    
    # Ensure we have proper Markdown structure
    if not re.search(r'#{1,6}\s', cleaned) and len(cleaned.split()) > 20:
        # If no headers but substantial content, add a default header
        cleaned = f"# Notes\n\n{cleaned}"
    
    # Ensure Next Steps section exists
    if "Next Steps" not in cleaned and "Action Items" not in cleaned:
        cleaned += "\n\n## Next Steps\n- Review and refine these notes\n- Take action on key points identified"
    
    return cleaned.strip()

def process_notes(input_path: Path, output_path: Path):
    """Process one note file into Markdown output."""
    start_total = time.time()
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    # Ensure model exists
    if not ensure_model():
        print("❌ Cannot proceed without model. Exiting.")
        logging.error("Model check failed. Exiting.")
        return False

    # Read notes
    try:
        with input_path.open("r", encoding="utf-8") as f:
            notes = f.read()
        logging.info(f"Loaded {len(notes)} characters from {input_path}")
        print(f"✅ Loaded {len(notes)} characters from {input_path.name}")
    except Exception as e:
        error_msg = f"❌ Failed to read {input_path}: {str(e)}"
        logging.error(error_msg)
        print(error_msg)
        return False

    # Build prompt
    logging.info("Building prompt...")
    print("📝 Building prompt...")
    prompt = build_prompt(notes)
    logging.info(f"Prompt built ({len(prompt)} characters)")
    print(f"✅ Prompt built ({len(prompt)} characters)")

    # Query model
    raw_output = ollama_query(prompt)
    
    # Clean output
    logging.info("Cleaning model output...")
    print("🧹 Cleaning model output...")
    enhanced_notes = clean_model_output(raw_output)
    
    if not enhanced_notes.strip():
        error_msg = "❌ Model returned empty content after cleaning"
        logging.error(error_msg)
        print(error_msg)
        return False

    # Save output
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(enhanced_notes)
        logging.info(f"Enhanced notes saved to {output_path}")
        print(f"✅ Enhanced notes saved to {output_path}")
    except Exception as e:
        error_msg = f"❌ Failed to write output file: {str(e)}"
        logging.error(error_msg)
        print(error_msg)
        return False

    total_elapsed = time.time() - start_total
    logging.info(f"Processed {input_path.name} in {total_elapsed:.2f}s")
    print(f"🎉 Completed processing in {total_elapsed:.2f}s")
    
    # Show preview of first few lines
    preview_lines = enhanced_notes.split('\n')[:5]
    preview = '\n'.join(preview_lines) + ("..." if len(enhanced_notes.split('\n')) > 5 else "")
    print("\n📄 Output preview:")
    print(preview)
    print()
    
    return True

def process_folder(input_folder: Path, output_folder: Path):
    """Process all unprocessed .txt files in a folder."""
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    
    start_all = time.time()
    processed = 0
    skipped = 0
    
    # Create output folder if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)
    
    for txt_file in input_folder.glob("*.txt"):
        output_file = output_folder / (txt_file.stem + ".md")
        
        if output_file.exists():
            msg = f"⏩ Skipping {txt_file.name} (already processed)"
            print(msg)
            logging.info(msg)
            skipped += 1
            continue
            
        print(f"\n📌 Processing {txt_file.name}...")
        if process_notes(txt_file, output_file):
            processed += 1
    
    total_all = time.time() - start_all
    summary = f"\n✅ Summary: {processed} processed, {skipped} skipped | Total time: {total_all:.2f}s"
    print(summary)
    logging.info(summary.strip())
    
    return processed > 0

def main():
    parser = argparse.ArgumentParser(
        description='Enhance raw notes into professional Markdown using AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('input', nargs='?', default=None,
                        help='Path to a note file or folder of notes (default: %(default)s)',
                        metavar='INPUT')
    parser.add_argument('output', nargs='?', default=None,
                        help='Path for output file or folder (default: %(default)s)',
                        metavar='OUTPUT')
    parser.add_argument('-m', '--model', default=MODEL_NAME,
                        help='Ollama model to use (default: %(default)s)')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Process even if output file exists')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed processing information')
    
    args = parser.parse_args()
    
    # Set global model if specified
    global MODEL_NAME
    MODEL_NAME = args.model
    
    # Determine input and output paths
    if args.input:
        input_path = Path(args.input)
        
        if input_path.is_file():
            # Single file processing
            if args.output:
                output_path = Path(args.output)
            else:
                # Default output in same folder with .md extension
                output_path = input_path.with_suffix('.md')
            
            # Setup logging specific to this file
            log_file = setup_logging(input_path)
            print(f"📝 Logging to: {log_file}")
            
            # Process the single file
            success = process_notes(input_path, output_path)
            
        elif input_path.is_dir():
            # Folder processing
            if args.output:
                output_folder = Path(args.output)
            else:
                output_folder = input_path / "Markdown Outputs"
            
            # Setup logging for folder processing
            log_file = setup_logging(input_path)
            print(f"📝 Logging to: {log_file}")
            
            # Process the folder
            success = process_folder(input_path, output_folder)
            
        else:
            print(f"❌ Input path '{input_path}' is neither a file nor a directory")
            sys.exit(1)
            
    else:
        # Default behavior - process default folders
        log_file = setup_logging(DEFAULT_INPUT_FOLDER)
        print(f"📝 Logging to: {log_file}")
        print(f"📁 Processing default folders:")
        print(f"   Input: {DEFAULT_INPUT_FOLDER}")
        print(f"   Output: {DEFAULT_OUTPUT_FOLDER}")
        success = process_folder(DEFAULT_INPUT_FOLDER, DEFAULT_OUTPUT_FOLDER)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()