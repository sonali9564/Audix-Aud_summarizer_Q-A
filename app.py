import streamlit as st
from pydub import AudioSegment
import tempfile
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

def summarize_audio(audio_file_path):
    """Summarize the audio using Google's Generative AI."""
    try:
        model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
        audio_file = genai.upload_file(path=audio_file_path)
        response = model.generate_content(
            [
                "Please summarize the following audio.",
                audio_file
            ]
        )
        return response.text
    except Exception as e:
        st.error(f"Error during summarization: {str(e)}")
        return None

def answer_question(audio_file_path, question):
    """Answer a question based on the audio content using Google's Generative AI."""
    try:
        model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
        audio_file = genai.upload_file(path=audio_file_path)
        response = model.generate_content(
            [
                f"Based on the following audio, answer this question: {question}",
                audio_file
            ]
        )
        return response.text  
    except Exception as e:
        st.error(f"Error during Q&A: {str(e)}")
        return None
def save_uploaded_file(uploaded_file):
    """Save uploaded file to a temporary file and return the path."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.' + uploaded_file.name.split('.')[-1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    except Exception as e:
        st.error(f"Error handling uploaded file: {e}")
        return None

st.markdown("""
<div style="text-align: center;">
    <h1>Welcome to Audix 🎙️</h1>
    <h3><i>Your Go-To Audio Summarization and Q&A Application 🎧</i></h3>
</div>
""", unsafe_allow_html=True)

with st.expander("**About this app**"):
    st.write("""
        This app uses Google's Gemini 1.5 Pro Model to:
        - Summarize audio files.
        - Answer questions based on the content of the uploaded audio.
        - Upload your audio files in WAV, MP3, MP4, or OGG format and easily obtain a summary or ask specific questions related to the content.
        - Save time and effort—no need to listen to the whole audio anymore!
    """)

audio_files = st.file_uploader("Upload Audio Files", type=['wav', 'mp3', 'mp4', 'ogg'], accept_multiple_files=True)

for audio_file in audio_files:
    audio_id = f"audio_{audio_file.name}"
    audio_path = save_uploaded_file(audio_file)
    st.audio(audio_path)

    if audio_id not in st.session_state:
        st.session_state[audio_id] = {"chat_session": [], "summary": None}

    if st.button(f'Summarize Audio - {audio_file.name}', key=f'summarize_{audio_file.name}'):
        with st.spinner(f'Summarizing {audio_file.name}...'):
            summary_text = summarize_audio(audio_path)
            if summary_text:
                st.session_state[audio_id]["summary"] = summary_text
                st.info(summary_text)

    if "summary" in st.session_state[audio_id] and st.session_state[audio_id]["summary"]:
        st.subheader(f"Summary for {audio_file.name}")
        st.write(st.session_state[audio_id]["summary"])

    st.subheader(f"Ask Questions About {audio_file.name}")
    question = st.text_input(f"Enter your question about {audio_file.name}:", key=f"question_{audio_file.name}")
    if question:
        if st.button(f'Get Answer for {audio_file.name}', key=f'get_answer_{audio_file.name}'):
            with st.spinner(f'Finding answer for {audio_file.name}...'):
                answer_text = answer_question(audio_path, question)
                if answer_text:
                    st.session_state[audio_id]["chat_session"].append({"role": "user", "text": question})  # User's question
                    st.session_state[audio_id]["chat_session"].append({"role": "assistant", "text": answer_text})  # Assistant's answer
                    st.info(answer_text)

    for message in st.session_state[audio_id]["chat_session"]:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])
