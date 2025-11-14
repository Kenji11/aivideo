import json
from pathlib import Path
from typing import Dict

TEMPLATES_DIR = Path(__file__).parent

def load_template(template_name: str) -> Dict:
    """Load template JSON file"""
    template_path = TEMPLATES_DIR / f"{template_name}.json"
    
    if not template_path.exists():
        raise ValueError(f"Template '{template_name}' not found")
    
    with open(template_path, 'r') as f:
        return json.load(f)

def list_templates() -> list:
    """List available templates"""
    return [
        "product_showcase",
        "lifestyle_ad",
        "announcement"
    ]

def validate_template_choice(template_name: str) -> bool:
    """Check if template exists"""
    return template_name in list_templates()

