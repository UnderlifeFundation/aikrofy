import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), '../backend/.env'))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

api_key = os.getenv('OPENAI_API_KEY')
print(f"Loaded API key (starts with): {api_key[:10] if api_key else 'None'}")

model = 'gpt-5-nano'
print(f"Testing ChatOpenAI with model: {model}")

try:
    chat = ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=1.0
    )
    res = chat.invoke([HumanMessage(content="Hola, ¿quién eres?")])
    print(f"Success! Response: {res.content}")
except Exception as e:
    print(f"ERROR: {e}")
