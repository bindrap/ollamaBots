Overview
This project converts handwritten or typed project notes from images into structured, professional project plans using AI-powered OCR and natural language processing. Simply take a photo of your project notes, and this tool will transform them into a well-organized markdown document with all the essential project planning elements.

Key Features
📸 Image to Text Conversion: Extract text from handwritten or typed notes using state-of-the-art vision models
🤖 AI-Powered Analysis: Transform messy notes into structured project plans with logical organization
📝 Professional Output: Generate markdown documents with all essential project planning sections
🔧 Modular Design: Easily extendable architecture for adding new features and capabilities
🌐 Local Processing: Runs entirely on your machine with no data sent to external servers
Project Structure
Image2Text/
├── orchestrator.py         # Main workflow controller
├── image2text.py           # Converts images to text using vision models
├── text2project.py         # Transforms raw text into structured project plans
├── Image/                  # (Directory for input images)
│   └── example.jpg         # Sample image to test with
├── project.md              # (Example output file)
└── README.md               # This documentation file

Installation & Setup
Prerequisites
Python 3.10+
Ollama (for running local AI models)
Optional: OpenCV for image preprocessing (pip install opencv-python)
Step-by-Step Setup
Install Ollama:
    # Windows: Download from https://ollama.com/download
    # Mac: brew install ollama
    # Linux: curl -fsSL https://ollama.com/install.sh | sh

Install required Python packages
    # pip install requests opencv-python

Download necessary AI models
    # ollama pull qwen2.5vl:7b     # For image understanding (OCR)
    # ollama pull qwen3:4b         # For text analysis and planning

Usage
Basic Workflow
Place your project notes image in the Image/ directory
Run the orchestrator with your image and desired output file
    # python orchestrator.py Image/your_notes.jpg project_plan.md
Check the generated project_plan.md file
# Process a sample image
python orchestrator.py Image/projNote.webp project.md

# Expected output:
# [INFO] Running OCR on projNote.webp...
# [OK] OCR complete
# [INFO] Analyzing project notes from projNote.webp...
# [OK] Project plan saved to project.md

Customization Options
Changing AI Models
Edit image2text.py and text2project.py to use different models:
# In image2text.py - for better image understanding
MODEL = "llama3.2-vision:latest"  # Alternative vision model

# In text2project.py - for more detailed planning
MODEL = "qwen3:8B"  # More powerful but slower model

Adjusting Output Format
Modify the prompt in text2project.py to change the structure of the output:
prompt = f"""
Convert this raw project notes into a structured project plan:

{text}

IMPORTANT: Output ONLY the project plan in markdown format. Start with "# Project Title" and nothing else.
"""

Integrating with Project Management Tools
The generated markdown can be easily imported into:

Notion (paste directly)
Obsidian (save as .md file)
Confluence (use markdown import)
GitHub/GitLab (as documentation)
Future Development
This project is designed to be extensible. Potential future enhancements include:

📊 Data Visualization: Automatically generate Gantt charts from timeline data
🌐 Web Interface: Create a browser-based dashboard for easier use
🤖 AI Assistant: Add chat interface for refining project plans
🔗 Integration: Connect with project management APIs (Jira, Trello)
📱 Mobile App: Companion app for capturing notes on-the-go