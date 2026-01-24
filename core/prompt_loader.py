import os
import yaml
from langchain.prompts import PromptTemplate


# Get prompt directory from environment or fallback to a default
PROMPT_DIR = os.getenv("PROMPTS_DIR", "app/prompts")



def escape_backslashes(text: str) -> str:
    return text.replace("\\", "\\\\")

def load_yaml_prompts(prompt_dir: str = PROMPT_DIR):
    """
    Load all YAML prompt files as PromptTemplate objects.
    Each YAML must define: name, prompt, and optional input_variables.
    """
    prompts = {}

    if not os.path.isdir(prompt_dir):
        raise FileNotFoundError(f"Prompt directory not found: {prompt_dir}")

    for file_name in os.listdir(prompt_dir):
        if not (file_name.endswith(".yaml") or file_name.endswith(".yml")):
            continue

        file_path = os.path.join(prompt_dir, file_name)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"Error reading {file_name}: {e}")
            continue

        if not data or "prompt" not in data or "name" not in data:
            print(f"Skipping invalid prompt file: {file_name}")
            continue

        name = data["name"]
        input_vars = data.get("input_variables", [])
        prompt_text = data["prompt"]

        # Updated: Use Jinja2 template format to safely handle LaTeX braces
        prompts[name] = PromptTemplate(
            input_variables=input_vars,
            template= escape_backslashes(prompt_text),
            template_format="f-string" 
        )

    return prompts



# Load all prompts at import time
PROMPTS = load_yaml_prompts()
