"""Model configuration and management"""

from anthropic import Anthropic
import os
import json
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# Default model
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

# Config file paths
CONFIG_FILE = "config/model_settings.json"
MODELS_CACHE_FILE = "config/models_cache.json"
CACHE_DURATION_HOURS = 24  # Cache models for 24 hours

def fetch_models_from_api(api_key: str = None) -> Optional[List[Dict]]:
    """
    Fetch available models from Anthropic API.
    Returns list of models or None if API call fails.
    """
    if not api_key:
        api_key = os.getenv('ANTHROPIC_API_KEY')

    if not api_key:
        return None

    try:
        response = requests.get(
            'https://api.anthropic.com/v1/models',
            headers={
                'anthropic-version': '2023-06-01',
                'X-Api-Key': api_key
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
        else:
            print(f"API returned status {response.status_code}")
            return None

    except Exception as e:
        print(f"Failed to fetch models from API: {e}")
        return None

def get_cached_models() -> Optional[Dict]:
    """Load models from cache if still valid"""
    if not os.path.exists(MODELS_CACHE_FILE):
        return None

    try:
        with open(MODELS_CACHE_FILE, 'r') as f:
            cache = json.load(f)

        # Check if cache is still valid
        cached_time = datetime.fromisoformat(cache.get('cached_at', '2000-01-01'))
        if datetime.now() - cached_time < timedelta(hours=CACHE_DURATION_HOURS):
            return cache
        else:
            return None

    except Exception as e:
        print(f"Failed to load cache: {e}")
        return None

def save_models_cache(models: List[Dict]):
    """Save fetched models to cache"""
    try:
        os.makedirs('config', exist_ok=True)
        cache = {
            'cached_at': datetime.now().isoformat(),
            'models': models
        }
        with open(MODELS_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Failed to save cache: {e}")

def get_fallback_models() -> List[Dict[str, str]]:
    """
    Fallback list of known Claude models.
    Used when API is unavailable.
    """
    return [
        {
            "id": "claude-3-5-sonnet-20241022",
            "display_name": "Claude 3.5 Sonnet (Latest)",
            "description": "Most intelligent model, best for complex tasks",
            "recommended": True
        },
        {
            "id": "claude-3-5-haiku-20241022",
            "display_name": "Claude 3.5 Haiku",
            "description": "Fastest model, good for simple tasks"
        },
        {
            "id": "claude-3-opus-20240229",
            "display_name": "Claude 3 Opus",
            "description": "Previous generation, very capable"
        },
        {
            "id": "claude-3-sonnet-20240229",
            "display_name": "Claude 3 Sonnet",
            "description": "Previous generation, balanced"
        },
        {
            "id": "claude-3-haiku-20240307",
            "display_name": "Claude 3 Haiku",
            "description": "Previous generation, fast"
        }
    ]

def enhance_model_info(models: List[Dict]) -> List[Dict[str, str]]:
    """
    Add descriptions and recommendations to API model data.
    """
    # Model name to description mapping
    descriptions = {
        'sonnet-4': 'Latest and most capable model',
        'opus-4': 'Most capable Opus model',
        'sonnet': 'Most intelligent model, best for complex tasks',
        'opus': 'Powerful model for complex reasoning',
        'haiku': 'Fastest model, good for simple tasks'
    }

    enhanced = []
    for model in models:
        model_id = model.get('id', '')
        display_name = model.get('display_name', model_id)

        # Determine description
        description = 'Claude model'
        for key, desc in descriptions.items():
            if key.lower() in model_id.lower() or key.lower() in display_name.lower():
                description = desc
                break

        # Mark latest Sonnet as recommended
        recommended = 'sonnet-4' in model_id.lower() or (
            'sonnet' in model_id.lower() and '3-5' in model_id
        )

        enhanced.append({
            'id': model_id,
            'display_name': display_name,
            'description': description,
            'recommended': recommended
        })

    return enhanced

def get_available_models(force_refresh: bool = False) -> List[Dict[str, str]]:
    """
    Get available models - tries API first, falls back to cache, then hardcoded list.

    Args:
        force_refresh: If True, bypasses cache and fetches from API
    """
    # Try cache first (unless force refresh)
    if not force_refresh:
        cached = get_cached_models()
        if cached:
            # Silently use cached models (don't spam console)
            return cached.get('models', get_fallback_models())

    # Try fetching from API
    print("Fetching models from Anthropic API...")
    api_models = fetch_models_from_api()

    if api_models:
        enhanced_models = enhance_model_info(api_models)
        save_models_cache(enhanced_models)
        print(f"Fetched {len(enhanced_models)} models from API")
        return enhanced_models
    else:
        print("Using fallback model list")
        return get_fallback_models()

def verify_model_works(model_id: str, api_key: str = None) -> bool:
    """
    Test if a model ID works with the API.
    """
    if not api_key:
        api_key = os.getenv('ANTHROPIC_API_KEY')

    if not api_key:
        return False

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model_id,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        return True
    except Exception as e:
        print(f"Model {model_id} verification failed: {e}")
        return False

def get_model_display_name(model_id: str) -> str:
    """Get friendly display name for model ID"""
    models = get_available_models()
    for model in models:
        if model['id'] == model_id:
            return model.get('display_name', model.get('name', model_id))
    return model_id

def save_model_config(model_id: str):
    """Save selected model to config file"""
    os.makedirs('config', exist_ok=True)
    config = {
        'selected_model': model_id,
        'model_name': get_model_display_name(model_id)
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_model_config() -> str:
    """Load selected model from config file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('selected_model', DEFAULT_MODEL)
        except:
            return DEFAULT_MODEL
    return DEFAULT_MODEL

def get_current_model() -> str:
    """Get the currently configured model"""
    return load_model_config()
