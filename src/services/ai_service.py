import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Constants
DEFAULT_MODEL = "models/gemini-2.0-flash"  # Latest and most capable model
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class LLMServiceError(Exception):
    """Custom exception for LLM service errors."""
    pass

class AIService:
    pass

def list_available_models():
    """List all available models for debugging."""
    if not GOOGLE_API_KEY:
        print("GOOGLE_API_KEY not set in environment.")
        return []
    
    genai.configure(api_key=GOOGLE_API_KEY)  # type: ignore
    
    try:
        models = genai.list_models()  # type: ignore
        available_models = []
        print("Available models:")
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                print(f"  - {model.name}")
                available_models.append(model.name)
        return available_models
    except Exception as e:
        print(f"Error listing models: {e}")
        return []

async def call_llm(prompt, model=DEFAULT_MODEL, system_prompt=None, max_tokens=512):
    if not GOOGLE_API_KEY:
        raise LLMServiceError("GOOGLE_API_KEY not set in environment.")
    
    # Configure the API key
    genai.configure(api_key=GOOGLE_API_KEY) #type: ignore
    
    try:
        # Create the model
        model_instance = genai.GenerativeModel(model) #type: ignore
        
        # Generate content with generation config
        response = await model_instance.generate_content_async(
            prompt,
            generation_config={
                "max_output_tokens": max_tokens
            }
        )
        return response.text
    except Exception as e:
        raise LLMServiceError(f"LLM call failed: {e}")

# Usage example (remove or comment out in production):
# if __name__ == "__main__":
#     import asyncio
#     
#     # First, list available models
#     print("Checking available models...")
#     list_available_models()
#     
#     # Test with the LLM
#     async def test():
#         try:
#             result = await call_llm("Explique la recette d'une pizza margherita.")
#             print(f"Success: {result}")
#         except Exception as e:
#             print(f"Error: {e}")
#     
#     asyncio.run(test())

# Note: Requires 'python-dotenv' and 'google-generativeai' packages.