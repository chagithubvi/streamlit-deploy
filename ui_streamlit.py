
import streamlit as st
import os
import random
from ui_intentstr import (
    get_speech_input, is_smart_home_command, smart_home_response,
    is_smart_home_question, chat_with_Aayva, is_admin_command, get_time_by_location ,
    is_continuation_of_smart_home_command, play_tts, aayva_response_from_text ,
    ChatGroq, API_KEY, MODEL 
)


API_KEY = os.getenv("API_KEY")
DEEPGRAM_KEY = os.getenv("DEEPGRAM_KEY")
MODEL = os.getenv("MODEL")


st.markdown("""
    <h1 style='color: #2C3E50; font-weight: 700;'>
        Aiva: Your Smart Home Assistant
    </h1>
""", unsafe_allow_html=True)


# Session state
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "chat_model" not in st.session_state:
    st.session_state.chat_model = ChatGroq(groq_api_key=API_KEY, model=MODEL)
if "awaiting_tts" not in st.session_state:
    st.session_state.awaiting_tts = False

# Display chat
for entry in st.session_state.conversation_history:
    # User
    col1, col2 = st.columns([0.3, 0.7])
    with col2:
        st.markdown(f"""
        <div style='text-align: right; background-color: #DCF8C6; color:#1C3F73; padding: 10px 15px; border-radius: 15px; margin: 5px;'>
            <b>You:</b> {entry['user']}
        </div>
        """, unsafe_allow_html=True)
    # Aayva
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.markdown(f"""
        <div style='text-align: left; background-color: #E4E6EB; color: #1C3F73; padding: 10px 15px; border-radius: 15px; margin: 5px;'>
            <b>Aiva:</b> {entry['aayva'] if entry['aayva'] else "..."}
        </div>
        """, unsafe_allow_html=True)

# Mic button styling
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color:#00B8A9;
        border-radius: 50%;
        font-size: 24px;
        width: 60px;
        height: 60px;
        position: fixed;
        bottom: 60px;
        left: 75%;
        transform: translateX(-50%);
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: none;
    }
    div.stButton > button:first-child:active {
        background-color: #0056b3;
    }
    </style>
""", unsafe_allow_html=True)

# Mic logic
if st.button("🔊", key="mic_button"):
    st.toast("Listening...")
    user_input = get_speech_input()

    aayva_response, updated_history = aayva_response_from_text(
    user_input, st.session_state.chat_model, st.session_state.conversation_history
)
    st.session_state.conversation_history = updated_history

    st.session_state.awaiting_tts = True
    st.rerun()  # Show UI update first

# Play TTS if flagged
if st.session_state.awaiting_tts and st.session_state.conversation_history:
    last = st.session_state.conversation_history[-1]
    if last["aayva"]:
        play_tts(last["aayva"])
        st.session_state.awaiting_tts = False
