# Process a single note
python noteBot.py "C:\Notes\meeting.txt" "C:\Notes\Enhanced\meeting.md"

# Process all notes in a folder
python noteBot.py "C:\Notes\ProjectA"

# Use a different model
python noteBot.py "note.txt" -m "qwen3:8b"

Detailed help with python noteBot.py --help showing all options
Clear visual feedback with emoji indicators for each processing step
2. Enhanced Output Quality
Qwen-specific prompt formatting using <|im_start|> tokens for better results
Multi-pattern cleaning that removes all forms of "thinking" text
Automatic structure validation to ensure proper Markdown format
Next Steps section guaranteed to exist in output
Output preview showing the first few lines of the enhanced note
3. Reliability Improvements
Dual API/CLI fallback - tries API first, falls back to CLI if needed
Robust model checking that handles different Ollama output formats
Comprehensive error handling at every step
Model quality indicator showing relative capability (8/10 for qwen3:4b)
Detailed logging organized by input file
4. Additional Features to Consider
Template system - let users define custom Markdown templates:
    python noteBot.py note.txt -t meeting
Would use a templates/meeting.md template for consistent formatting
Integration with note-taking apps:
Obsidian plugin support
Notion API integration
OneNote export capability
    python noteBot.py note.txt --backup
Content tagging
    python noteBot.py note.txt --tags "project,meeting"
Would add YAML front matter with tags for knowledge management systems
Batch processing with filters
    python noteBot.py Notes/ --filter "weekly-*.txt"
Quality-of-life improvements:
Progress bar for long-running operations
Option to open output file automatically when done
Support for more input formats (PDF, DOCX with optional dependencies)
Usage Examples
Basic Single File Processing
    python noteBot.py "C:\Notes\project_ideas.txt" "C:\Notes\Enhanced\project_plan.md"
Using a Different Model
    python noteBot.py "meeting_notes.txt" -m "qwen3:8b"
Processing an Entire Folder
    python noteBot.py "C:\Notes\ProjectAlpha"
Using Default Folders
    python noteBot.py