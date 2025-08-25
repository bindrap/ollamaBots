import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime
import re

# ====== Configuration ======
OLLAMA_PATH = r"C:\Users\bindrap\AppData\Local\Programs\Ollama\ollama.exe"
PROJECT_PROMPT_FILE = Path(r"C:\Users\bindrap\Documents\syntaxBot\prompt.txt")
INPUT_FOLDER = Path(r"C:\Users\bindrap\Documents\syntaxBot\SQL")
OUTPUT_FOLDER = INPUT_FOLDER / "SyntaxReports"
MODEL_NAME = "codellama:7b-instruct"  # Change model as needed

# ====== Logging Setup ======
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = OUTPUT_FOLDER / f"{timestamp}.log"
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ====== Rule Loader ======
def load_project_prompt() -> str:
    if PROJECT_PROMPT_FILE.exists():
        return PROJECT_PROMPT_FILE.read_text(encoding="utf-8")
    else:
        logging.error(f"Project prompt file {PROJECT_PROMPT_FILE} not found.")
        return ""

def load_resultcode_rules() -> dict:
    """Extract expected ResultCode mappings from prompt.txt."""
    rules = {}
    try:
        text = PROJECT_PROMPT_FILE.read_text(encoding="utf-8")
        for line in text.splitlines():
            match = re.match(r"ResultCode\s*=\s*(\d+)\s*->\s*(.+)", line.strip(), re.I)
            if match:
                code, desc = match.groups()
                rules[code] = desc.strip()
        logging.info(f"Loaded {len(rules)} ResultCode rules from {PROJECT_PROMPT_FILE}")
    except FileNotFoundError:
        logging.error(f"{PROJECT_PROMPT_FILE} not found. Skipping ResultCode validation.")
    return rules

# ====== Ollama Helpers ======
def ensure_model(model: str):
    """Ensure the Ollama model exists locally."""
    print(f"🔍 Checking if model '{model}' exists locally...")
    try:
        result = subprocess.run([OLLAMA_PATH, "list"], capture_output=True, text=True, check=True)
        models = [line.split()[0] for line in result.stdout.strip().splitlines()]
        if model not in models:
            print(f"📥 Model '{model}' not found. Downloading...")
            subprocess.run([OLLAMA_PATH, "pull", model], check=True)
            print(f"✅ Model '{model}' downloaded.")
        else:
            print(f"✅ Model '{model}' is already available.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error checking/downloading model: {e}")

def ollama_query(model: str, prompt: str, timeout: int = 1200) -> str:
    """Query Ollama model and return output."""
    start = time.time()
    try:
        result = subprocess.run(
            [OLLAMA_PATH, "run", model, "--hidethinking"],
            input=prompt.encode(),
            capture_output=True,
            timeout=timeout
        )
        result.check_returncode()
        elapsed = time.time() - start
        logging.info(f"Model responded in {elapsed:.2f}s")
        return result.stdout.decode().strip()
    except subprocess.TimeoutExpired:
        logging.warning("Model query timed out.")
        return "⚠️ Model query timed out."
    except subprocess.CalledProcessError as e:
        logging.warning(f"Ollama failed: {e.stderr.decode().strip()}")
        return f"⚠️ Ollama failed: {e.stderr.decode().strip()}"

# ====== SQL Analysis ======
def analyze_sql(sql_text: str, rules: dict) -> dict:
    """Static SQL analysis: ResultCodes, status changes, redundancy, best practices."""
    analysis = {
        "resultcodes_found": [],
        "missing_resultcodes": [],
        "status_changes": [],
        "unused_blocks": [],
        "best_practices": []
    }

    lines = sql_text.splitlines()

    # ---- ResultCodes ----
    for i, line in enumerate(lines, start=1):
        for match in re.finditer(r"=\s*(\d{3,5})", line):
            code = match.group(1)
            analysis["resultcodes_found"].append((i, code))
            if code not in rules:
                analysis["best_practices"].append(f"⚠️ Line {i}: Unexpected ResultCode {code} (not in rules)")

    # Check missing rules
    for expected in rules.keys():
        if expected not in [c for _, c in analysis["resultcodes_found"]]:
            analysis["missing_resultcodes"].append(expected)

    # ---- Status updates ----
    for i, line in enumerate(lines, start=1):
        if re.search(r"UPDATE\s+Folder.*StatusCode\s*=", line, re.I):
            analysis["status_changes"].append(f"Line {i}: Folder status updated")
        if re.search(r"UPDATE\s+Process.*StatusCode\s*=", line, re.I):
            analysis["status_changes"].append(f"Line {i}: Process status updated")

    # ---- Redundant / Unused blocks ----
    if "BEGIN" in sql_text and "END" not in sql_text:
        analysis["unused_blocks"].append("⚠️ BEGIN without END detected")
    if "IF EXISTS" in sql_text and "DROP" not in sql_text:
        analysis["unused_blocks"].append("⚠️ IF EXISTS without DROP usage")

    # ---- Best practices ----
    if not re.search(r"TRY\s+BEGIN", sql_text, re.I):
        analysis["best_practices"].append("⚠️ Missing TRY/CATCH error handling")
    if "DECLARE @" not in sql_text:
        analysis["best_practices"].append("⚠️ Missing variable declarations")
    if "SELECT *" in sql_text.upper():
        analysis["best_practices"].append("⚠️ Avoid SELECT * (use explicit columns)")
    if len(re.findall(r"\bUPDATE\b", sql_text, re.I)) > 3:
        analysis["best_practices"].append("⚠️ Too many UPDATEs – consider DRY principle")

    return analysis

# ====== Prompt Builder ======
def build_prompt(project_logic: str, sql_code: str, filename: str, static_analysis: dict) -> str:
    return f"""
You are a SQL syntax and logic checker for a city project.

Project rules and assumptions:
{project_logic}

SQL file: {filename}
SQL code:
{sql_code}

Static Analysis Results:
- ResultCodes Found: {static_analysis['resultcodes_found']}
- Missing ResultCodes: {static_analysis['missing_resultcodes']}
- Status Changes: {static_analysis['status_changes']}
- Unused Blocks: {static_analysis['unused_blocks']}
- Best Practices: {static_analysis['best_practices']}

Tasks:
- Verify correctness of ResultCodes vs rules.
- Identify missing ResultCodes and logic issues.
- Check Process/Folder status update logic.
- Detect unused/redundant code blocks.
- Recommend SQL best practices (naming, DRY, error handling, variable declarations).
- Suggest corrections if needed.

Output as structured Markdown:
# {filename}
## Syntax Errors / Warnings
## Logic or Rule Violations
## Suggested Fixes
"""

# ====== File Processor ======
def process_sql_file(file_path: Path, project_logic: str, rules: dict):
    logging.info(f"Processing {file_path.name}")
    print(f"📂 Checking {file_path.name}...")

    sql_code = file_path.read_text(encoding="utf-8")
    static_analysis = analyze_sql(sql_code, rules)
    prompt = build_prompt(project_logic, sql_code, file_path.name, static_analysis)

    output = ollama_query(MODEL_NAME, prompt)

    report_file = OUTPUT_FOLDER / (file_path.stem + "_report.md")
    report_file.write_text(output, encoding="utf-8")

    logging.info(f"Report saved to {report_file}")
    print(f"✅ Report saved to {report_file.name}")

# ====== Folder Processor ======
def process_folder(input_folder: Path):
    start_all = time.time()
    project_logic = load_project_prompt()
    if not project_logic:
        print("⚠️ Project prompt is empty. Aborting.")
        return

    rules = load_resultcode_rules()
    ensure_model(MODEL_NAME)

    for sql_file in input_folder.glob("*.sql"):
        process_sql_file(sql_file, project_logic, rules)

    elapsed_all = time.time() - start_all
    logging.info(f"All files processed in {elapsed_all:.2f}s")
    print(f"🎉 All files processed in {elapsed_all:.2f}s")
    print(f"📝 Logs saved at {log_file}")

# ====== Main Execution ======
if __name__ == "__main__":
    process_folder(INPUT_FOLDER)
