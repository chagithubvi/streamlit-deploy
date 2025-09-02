from dotenv import load_dotenv
load_dotenv()
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from langchain_core._api.deprecation import LangChainDeprecationWarning
from deepgram import Deepgram
import word2number as w2n
from zoneinfo import ZoneInfo
from zoneinfo import available_timezones
from datetime import datetime
import streamlit as st
import edge_tts
import tempfile
from audio_recorder_streamlit import audio_recorder
import io
import asyncio
import numpy as np
import warnings
import random
import re
import os
import base64
from scipy.io.wavfile import write

# Configured values
API_KEY = os.getenv("API_KEY")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_KEY")  
MODEL = os.getenv("MODEL")
VOICE = "en-US-JennyNeural"
SAMPLE_RATE = 16000
FRAME_DURATION = 30 
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)
BUFFER_DURATION = 0.5   #Seconds to wait to stop synthes

chat_model = ChatGroq(api_key=API_KEY, model_name=MODEL)

warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)

# --- Constants ---
SMART_HOME_KEYWORDS = [
    "turbine", "wind turbine", "home turbine", "power", "gear", "louvers",
    "battery status", "diagnostic", "speed", "standby", "lights", "fan", "ac", "air conditioner", "heater", "thermostat",
    "temperature", "door", "lock", "unlock", "spotlight", "humidifier", "curtain"
]

SMART_HOME_ACTION = [
    "turn on", "shut off", "set", "check", "switch", "store", "notify",
    "run", "automate", "open", "adjust", "gear", "turn off", "switch on", "switch off", "set", "increase", "decrease",
    "open", "close", "lock", "unlock"
]

ADMIN_KEYWORDS = [
    "wifi" , "wi-fi" , "new user" , "family" , "password" , "family members" , "access" ,
]

ADMIN_ACTION = [
    "grant" , "give" , "change" , "add" , "remove" , "show"
]

GOODBYE_PHRASES = {"exit", "goodbye", "bye", "see you", "see you later", "talk to you later"}
GOODBYES = [
    "See you soon!", "Goodbye for now!", "Catch you later!", "Talk to you soon!",
    "Take care!", "Bye-bye!", "Until next time!"
]

VALID_GEARS = {"1", "3", "6", "18" } 

FAQ_RESPONSES = {
    "what is enercea": "Enercea is a company that builds homes and communities that generate their own clean energy, helping people live without paying utility bills.",
    "where is enercea": "Our global headquarters is in Flint City, Michigan, USA.",
    "what do they work on": "We work on BEHBs—Battery Electric Homes and Buildings—and DAKET engines for off-grid, smart, resilient communities.",
    "who built you": "Developed by Enercea to help manage your smart, sustainable living environment.",
    "who created you": "I was developed by Enercea, a clean-tech innovation company.",
    "your company": "I'm part of Enercea’s smart home ecosystem.",
    "who made you": "Enercea built me to support your battery-electric lifestyle.",
}

ADMIN_RESPONSES = [
    "That sounds like an admin-level command. Do you have the necessary access?",
    "I can’t proceed unless you’re authorized for admin operations.",
    "This action requires hoisted operations. Please authenticate first."
]

# --- Utility Functions ---
def is_smart_home_command(user_input):
    input_lower = user_input.lower()
    return (
        any(keyword in input_lower for keyword in SMART_HOME_KEYWORDS) and
        any(verb in input_lower for verb in SMART_HOME_ACTION)
    )

def get_time_by_location(user_input):
    ALIASES = {
        # US States
        "california": "America/Los_Angeles",
        "texas": "America/Chicago",
        "florida": "America/New_York",
        "new york": "America/New_York",
        "washington": "America/Los_Angeles",
        # Canadian Provinces
        "ontario": "America/Toronto",
        "british columbia": "America/Vancouver",
        "quebec": "America/Montreal",
        # Indian cities/states
        "mumbai": "Asia/Kolkata",
        "delhi": "Asia/Kolkata",
        "bangalore": "Asia/Kolkata",
        "maharashtra": "Asia/Kolkata",
        "gujarat": "Asia/Kolkata",
        # Countries
        "canada": "America/Toronto",
        "india": "Asia/Kolkata",
        "usa": "America/New_York",
        "united states": "America/New_York",
        "germany": "Europe/Berlin",
        "uk": "Europe/London",
        "united kingdom": "Europe/London"
    }

    match = re.search(r"\btime(?:.*in)? ([\w\s]+)", user_input.lower())
    if match:
        city_guess = match.group(1).strip().lower()
    else:
        city_guess = user_input.lower().split()[-1]

    # Check alias first
    if city_guess in ALIASES:
        tz = ALIASES[city_guess]
        now = datetime.now(ZoneInfo(tz))
        city_name = tz.split("/")[-1].replace("_", " ")
        return f"The current time in {city_name.title()} is {now.strftime('%I:%M %p')}."

    # Fallback: fuzzy match to IANA zones
    for tz in available_timezones():
        if city_guess in tz.lower():
            now = datetime.now(ZoneInfo(tz))
            city_name = tz.split("/")[-1].replace("_", " ")
            return f"The current time in {city_name.title()} is {now.strftime('%I:%M %p')}."

    return None

def extract_gear_value(text):
    text = text.lower().strip()
    match = re.search(r"\bgear\s*(?:to|at)?\s*([\w\-]+)", text)
    if match:
        value = match.group(1).strip()
        try:
            # Try converting word to number first
            num = w2n.word_to_num(value)
            return str(num)
        except:
            # If already a digit (like '6'), return it as-is
            if value.isdigit():
                return value
    return None

def is_smart_home_question(user_input):
    input_lower = user_input.lower()
    question_indicators = ["?", "what", "status", "check", "notify", "diagnostic", "how much"]
    return (
        any(keyword in input_lower for keyword in SMART_HOME_KEYWORDS) and
        any(indicator in input_lower for indicator in question_indicators)
    )

def is_admin_command(user_input):
    input_lower = user_input.lower()
    return (
        any(keyword in input_lower for keyword in ADMIN_KEYWORDS) and
        any(verb in input_lower for verb in ADMIN_ACTION)
    )

def check_faq(user_input):
    input_lower = user_input.lower()
    for phrase, response in FAQ_RESPONSES.items():
        if phrase in input_lower:
            return response
    return None

def is_continuation_of_smart_home_command(conversation_history, user_input):
    if not conversation_history:
        return False
    last_exchange = conversation_history[-1]
    return is_smart_home_command(last_exchange['user']) and not is_smart_home_command(user_input) and not is_smart_home_question(user_input)

# --- TTS Function ---
def play_tts(response_text):
    tts_text = response_text.replace("Aiva", "Aayva")
    async def synthesize_and_return_audio(text):
        communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
        stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                stream.write(chunk["data"])
        stream.seek(0)
        return stream
    audio_stream = asyncio.run(synthesize_and_return_audio(tts_text))
    try:
        audio_bytes = audio_stream.read()
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        html_audio = f"""
            <audio autoplay style="display:none;">
                <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
            </audio>
        """
        st.markdown(html_audio, unsafe_allow_html=True)
    finally:
        audio_stream.close() 

# --- Smart Home Responses ---
def smart_home_response(user_input, chat_model, conversation_history):
    faq_answer = check_faq(user_input)
    if faq_answer:
        return faq_answer

    history_text = "\n".join(
        [f"User: {x['user']}\nAiva: {x['aayva']}" for x in conversation_history[-3:]]
    )

    gear_val = extract_gear_value(user_input)
    if gear_val:
        gear_val = gear_val.strip()
        if gear_val in VALID_GEARS:
            system_prompt = SystemMessage(content=(
                "You are Aiva, a smart home assistant who helps users control devices with ease. "
                "When the user gives a smart home command to set gear to a valid value, respond with one of these two options ONLY:\n"
                "Sure. Passing it to our smart home system.\n"
                "OR\n"
                "Of course. Passing it to our smart home system.\n"
                "Then follow up with a brief, natural comment or question specifically related to that command. "
                "Recent conversation:\n" + history_text
            ))
            messages = [system_prompt, HumanMessage(content=user_input)]
            response = chat_model.invoke(messages, temperature=0.7, max_tokens=35)
            return response.content.strip()
        else:
            return "Can't change, available gears are 1, 3, 6, and 18."

    if is_continuation_of_smart_home_command(conversation_history, user_input):
        return random.choice([
            "Sure. Passing it to our smart home system.",
            "Of course. Passing it to our smart home system."
        ])

    system_prompt = SystemMessage(content=(
        "You are Aiva, a smart home assistant who helps users control devices with ease. "
        "Do not include introductions like 'I'm your sidekick' or similar. "
        "When the user gives a smart home command, respond with one of these two options ONLY:\n"
        "'Sure. Passing it to our smart home system.'\n"
        "OR\n"
        "'Of course. Passing it to our smart home system.'\n"
        "Then follow up with a brief, natural comment or question specifically related to that command. "
        "Avoid repeating commands and keep responses under 30 words. "
        "Recent conversation:\n" + history_text
    ))
    messages = [system_prompt, HumanMessage(content=user_input)]
    response = chat_model.invoke(messages, temperature=0.7, max_tokens=35)
    return response.content.strip()

# --- Chat Response ---
def chat_with_Aayva(user_input, chat_model, conversation_history):
    faq_answer = check_faq(user_input)
    if faq_answer:
        return faq_answer

    history_text = "\n".join(
        [f"User: {x['user']}\nAiva: {x['aayva']}" for x in conversation_history[-3:]]
    )

    system_prompt = SystemMessage(content=(
        "You're Aiva, a warm, helpful smart home assistant. "
        "You respond briefly and casually, like texting a friend. "
        "Avoid long explanations unless the user asks for details. "
        "Make sure your response sounds more natural and friendly"
        "When the user says any goodbye words, respond with a warm, varied farewell. "
        "Keep responses under 30 words."
        "Recent conversation:\n" + history_text
    ))
    messages = [system_prompt, HumanMessage(content=user_input)]
    response = chat_model.invoke(messages, temperature=0.7, max_tokens=75)
    return response.content.strip()

# --- Speech Input ---
def get_speech_input(audio_bytes):
    if not audio_bytes:  # Handle None or empty audio_bytes
        return ""
    
    wav_buffer = io.BytesIO(audio_bytes)
    dg_client = Deepgram(DEEPGRAM_KEY)
    source = {'buffer': wav_buffer, 'mimetype': 'audio/wav'}
    try:
        response = asyncio.run(
            dg_client.transcription.prerecorded(
                source,
                {
                    'model': 'nova',
                    'punctuate': True,
                    'smart_format': True
                }
            )
        )
        transcript = response['results']['channels'][0]['alternatives'][0]['transcript']
        return transcript.strip()
    except Exception as e:
        st.error(f"Transcription error: {e}")
        return ""

# --- Main Loop ---
def aayva_response_from_text(user_input, chat_model, conversation_history):
    if user_input.lower() in GOODBYE_PHRASES:
        response = random.choice(GOODBYES)
    elif "time" in user_input.lower():
        response = get_time_by_location(user_input) or "Hmm, I couldn’t find the current time for that location."
    elif is_smart_home_command(user_input) or is_continuation_of_smart_home_command(conversation_history, user_input):
        response = smart_home_response(user_input, chat_model, conversation_history)
    elif is_smart_home_question(user_input):
        response = chat_with_Aayva(user_input, chat_model, conversation_history)
    elif is_admin_command(user_input):
        response = random.choice(ADMIN_RESPONSES)
    else:
        response = chat_with_Aayva(user_input, chat_model, conversation_history)

    conversation_history.append({"user": user_input, "aayva": response})
    return response, conversation_history