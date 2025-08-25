#!/usr/bin/env python3
"""
Interactive Ollama Code Generator and Fixer
===========================================
A streamlined and robust tool for generating code from prompts and fixing errors in files
using a local Ollama model.

Author: AI Assistant
Version: 3.1.0
License: MIT
"""
import subprocess
import time
import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
import sys
from typing import Optional

# ========= CONFIGURATION =========
@dataclass
class GeneratorConfig:
    """Basic configuration for the generator."""
    model_name: str = "qwen3:8b" #qwen2.5vl:7b (6gb) or qwen3:4B (2.5gb) or or codellama:7b (3.8gb) or qwen:8b (5.2gb)     8b times out after 15 minutes
    output_dir: Path = Path("output")
    timeout_minutes: int = 15  # Reduced timeout for more focused tasks

# ========= CORE GENERATOR =========
class CodeGenerator:
    """Handles the core logic of running Ollama and processing output."""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.logger = logging.getLogger("CodeGenerator")
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def _run_ollama(self, full_prompt: str) -> str:
        """
        Executes the Ollama process with a given prompt and captures the output.
        """
        cmd = ["ollama", "run", self.config.model_name]
        self.logger.info(f"Running model '{self.config.model_name}'...")

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            # Send the prompt to the model
            stdout, stderr = process.communicate(full_prompt, timeout=self.config.timeout_minutes * 60)

            if process.returncode != 0:
                error_message = f"Ollama process failed with code {process.returncode}:\n{stderr}"
                self.logger.error(error_message)
                raise RuntimeError(error_message)

            self.logger.info("Generation completed successfully.")
            return stdout.strip()

        except FileNotFoundError:
            self.logger.error("'ollama' command not found. Is Ollama installed and in your PATH?")
            raise
        except subprocess.TimeoutExpired:
            self.logger.error(f"Process timed out after {self.config.timeout_minutes} minutes.")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            raise

    def generate_from_prompt(self, user_prompt: str) -> str:
        """
        Generates code based on a user's text prompt.
        """
        self.logger.info("Starting code generation from prompt...")
        system_prompt = (
            "You are an expert programmer. Your task is to generate clean, efficient, and correct code based on the user's request. "
            "Provide only the code, without any explanations, introductions, or markdown formatting."
        )
        full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"
        
        generated_code = self._run_ollama(full_prompt)
        
        # Save the output to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.config.output_dir / f"generated_{timestamp}.py"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(generated_code)
        self.logger.info(f"Output saved to {output_file}")
        
        return generated_code

    def fix_from_file(self, file_path: Path, error_context: Optional[str] = None) -> str:
        """
        Reads code from a file, identifies errors, and generates a fixed version,
        optionally using provided error context.
        """
        self.logger.info(f"Starting code fixing for file: {file_path}...")
        if not file_path.exists():
            raise FileNotFoundError(f"The file '{file_path}' was not found.")

        try:
            original_code = file_path.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.error(f"Could not read file '{file_path}': {e}")
            raise

        system_prompt = (
            "You are an expert code debugger. Your task is to analyze the provided code, identify any errors or bugs, and provide a corrected, complete version of the code. "
            "Do not provide explanations, just the full, fixed code."
        )
        
        user_message = f"Please fix this code:\n\n```\n{original_code}\n```"
        
        if error_context:
            self.logger.info("Using provided error context to improve the fix.")
            user_message += f"\n\nHere is the error I'm getting or a description of the problem:\n{error_context}"

        full_prompt = f"System: {system_prompt}\n\nUser: {user_message}\n\nAssistant:"
        
        fixed_code = self._run_ollama(full_prompt)
        
        # Save the fixed code to a new file
        fixed_file_path = self.config.output_dir / f"{file_path.stem}_fixed.py"
        with open(fixed_file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_code)
        self.logger.info(f"Fixed code saved to {fixed_file_path}")
        
        return fixed_code

# ========= COMMAND LINE INTERFACE =========
def main_cli():
    """
    Simple command-line interface to run the generator.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python your_script_name.py generate \"<your prompt>\"")
        print("  python your_script_name.py fix <file_path> \"[optional error message or path to error_log.txt]\"")
        sys.exit(1)

    command = sys.argv[1]
    argument = sys.argv[2]

    config = GeneratorConfig()
    generator = CodeGenerator(config)

    try:
        if command == "generate":
            print("--- Generating Code ---")
            result = generator.generate_from_prompt(argument)
            print("\n--- Generated Code ---")
            print(result)
        elif command == "fix":
            print(f"--- Fixing File: {argument} ---")
            file_path = Path(argument)
            error_context = None
            
            # Check for an optional third argument (error message or file path)
            if len(sys.argv) > 3:
                context_arg = sys.argv[3]
                context_path = Path(context_arg)
                if context_path.is_file():
                    # It's a file, so read it
                    print(f"--- Reading error context from: {context_path} ---")
                    error_context = context_path.read_text(encoding='utf-8')
                else:
                    # It's not a file, so treat it as a string message
                    print("--- Using provided error message as context ---")
                    error_context = context_arg

            result = generator.fix_from_file(file_path, error_context)
            print("\n--- Fixed Code ---")
            print(result)
        else:
            print(f"Error: Unknown command '{command}'")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"Operation failed: {e}", exc_info=False)
        sys.exit(1)

# ========= MAIN BLOCK =========
if __name__ == "__main__":
    from datetime import datetime
    main_cli()
