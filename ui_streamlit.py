import streamlit as st
import os
from ui_intentstr import (
    get_speech_input, is_smart_home_command, smart_home_response,
    is_smart_home_question, chat_with_Aayva, is_admin_command, get_time_by_location,
    is_continuation_of_smart_home_command, play_tts, aayva_response_from_text,
    ChatGroq, API_KEY, MODEL
)
from audio_recorder_streamlit import audio_recorder

# Load API keys from environment
API_KEY = os.getenv("API_KEY")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_KEY")
MODEL = os.getenv("MODEL")

# Title
st.markdown("""
    <h1 style='color: #2C3E50; font-weight: 700;'>
        Aiva: Your Smart Home Assistant
    </h1>
""", unsafe_allow_html=True)

# Session State Initialization
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "chat_model" not in st.session_state:
    st.session_state.chat_model = ChatGroq(groq_api_key=API_KEY, model=MODEL)

if "awaiting_tts" not in st.session_state:
    st.session_state.awaiting_tts = False

if "text_input" not in st.session_state:
    st.session_state.text_input = ""


# --- Input Handlers ---
def handle_text_input():
    user_input = st.session_state.text_input.strip()
    if user_input:
        response, updated_history = aayva_response_from_text(
            user_input,
            chat_model=st.session_state.chat_model,
            conversation_history=st.session_state.conversation_history,
        )
        st.session_state.conversation_history = updated_history
        st.session_state.awaiting_tts = True
        st.session_state.text_input = ""  # Clear the input field


# --- Voice Input ---
audio_bytes = audio_recorder()
if audio_bytes:
    user_input = get_speech_input(audio_bytes)
    if user_input:
        response, updated_history = aayva_response_from_text(
            user_input,
            chat_model=st.session_state.chat_model,
            conversation_history=st.session_state.conversation_history,
        )
        st.session_state.conversation_history = updated_history
        st.session_state.awaiting_tts = True
    else:
        st.write("No speech detected. Please try again.")

# --- Text Input Widget ---
st.text_input("Or type here:", key="text_input", on_change=handle_text_input)


# --- Chat Display ---
for entry in st.session_state.conversation_history:
    # User
    col1, col2 = st.columns([0.3, 0.7])
    with col2:
        st.markdown(f"""
        <div style='text-align: right; background-color: #DCF8C6; color:#1C3F73; padding: 10px 15px; border-radius: 15px; margin: 5px;'>
            <b>You:</b> {entry['user']}
        </div>
        """, unsafe_allow_html=True)

    # Aiva
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.markdown(f"""
        <div style='text-align: left; background-color: #E4E6EB; color: #1C3F73; padding: 10px 15px; border-radius: 15px; margin: 5px;'>
            <b>Aiva:</b> {entry['aayva'] if entry['aayva'] else "..."}
        </div>
        """, unsafe_allow_html=True)

# --- TTS Playback ---
if st.session_state.awaiting_tts and st.session_state.conversation_history:
    last = st.session_state.conversation_history[-1]
    if last["aayva"]:
        play_tts(last["aayva"])
        st.session_state.awaiting_tts = False
