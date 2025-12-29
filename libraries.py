import os
import traceback
from dotenv import load_dotenv

# Import the NEW Gemini SDK
from google import genai
from groq import Groq
import pdfplumber

# Load environment variables
load_dotenv()

# Global variable to track last used model (backend only)
LAST_MODEL_USED = {
    'model': 'None',
    'provider': 'None',
    'gemini_available': False,
    'groq_available': False,
    'last_error': None
}

def init_models():
    global LAST_MODEL_USED
    
    print("Initializing AI Models...")
    
    # Check Gemini availability with NEW SDK
    gemini_key = os.getenv('GOOGLE_API_KEY')
    if gemini_key and gemini_key.strip():
        try:
            # Test with NEW SDK
            client = genai.Client(api_key=gemini_key)
            LAST_MODEL_USED['gemini_available'] = True
            print("Gemini API: Initialized successfully")
        except Exception as e:
            LAST_MODEL_USED['gemini_available'] = False
            print(f"Gemini API error: {str(e)[:100]}")
    else:
        LAST_MODEL_USED['gemini_available'] = False
        print("Gemini API: Key not found in .env")
    
    # Check Groq availability
    groq_key = os.getenv('GROQ_API_KEY')
    if groq_key and groq_key.strip():
        try:
            client = Groq(api_key=groq_key)
            LAST_MODEL_USED['groq_available'] = True
            print("Groq API: Initialized successfully")
        except Exception as e:
            LAST_MODEL_USED['groq_available'] = False
            print(f"Groq API error: {str(e)[:100]}")
    else:
        LAST_MODEL_USED['groq_available'] = False
        print("Groq API: Key not found in .env")
    
    return LAST_MODEL_USED

# Initialize on import
init_models()

def extract_text_from_pdf(filepath):
    try:
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        print(f"Extracted {len(text)} characters from PDF")
        return text.strip()
    except Exception as e:
        print(f"PDF extraction error: {str(e)}")
        return ""

def call_gemini_api(prompt, gemini_key):
    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        if response and response.text:
            return response.text.strip()
        return None
    except Exception as e:
        print(f"Gemini API error: {e}")
        return None

def call_groq_api(prompt, groq_key):
    """Call Groq API"""
    try:
        client = Groq(api_key=groq_key)
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            temperature=0.7,
            max_tokens=4000,
            timeout=30
        )
        
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Groq API error: {e}")
        return None

def call_ai_api(prompt):
    """Call AI API (Gemini with Groq fallback) - returns response only"""
    global LAST_MODEL_USED
    
    print("\n" + "="*60)
    print("Generating Portfolio using PortfolioGen")
    print("="*60)
    
    # Try Gemini first if available
    gemini_key = os.getenv('GOOGLE_API_KEY')
    if gemini_key and LAST_MODEL_USED['gemini_available']:
        try:
            print("Using Google Gemini AI")
            
            response = call_gemini_api(prompt, gemini_key)
            
            if response:
                LAST_MODEL_USED['model'] = 'Gemini'
                LAST_MODEL_USED['provider'] = 'Google'
                LAST_MODEL_USED['last_error'] = None
                
                print("Portfolio Generated Successfully")
                print(f"Content Length: {len(response)} Characters")
                print("="*60)
                
                return response
            else:
                print("Fail to call Google Gemini trying Groq...")
                
        except Exception as gemini_error:
            error_msg = str(gemini_error)
            LAST_MODEL_USED['last_error'] = error_msg
            
            if "429" in error_msg or "quota" in error_msg.lower():
                print("Primary service unavailable, using secondary service...")
            else:
                print(f"Primary service error, using secondary service: {error_msg[:100]}")
    
    # Try Groq as fallback if available
    groq_key = os.getenv('GROQ_API_KEY')
    if groq_key and LAST_MODEL_USED['groq_available']:
        try:
            print("Using Groq AI")
            
            response = call_groq_api(prompt, groq_key)
            
            if response:
                LAST_MODEL_USED['model'] = 'Groq'
                LAST_MODEL_USED['provider'] = 'Groq'
                LAST_MODEL_USED['last_error'] = None
                
                print("AI generation successful")
                print(f"Generated content length: {len(response)} characters")
                print("="*60)
                
                return response
            else:
                print("Secondary AI service returned empty response")
                
        except Exception as groq_error:
            error_msg = str(groq_error)
            LAST_MODEL_USED['last_error'] = error_msg
            print(f"Secondary service error: {error_msg[:200]}")
    
    # If both fail
    error_message = "All AI services unavailable"
    if LAST_MODEL_USED.get('last_error'):
        error_message += f": {LAST_MODEL_USED['last_error'][:200]}"
    
    print(error_message)
    print("="*60)
    
    raise Exception(error_message)

def get_last_model_used():
    global LAST_MODEL_USED
    return LAST_MODEL_USED.copy()