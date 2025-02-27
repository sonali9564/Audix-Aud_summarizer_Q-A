import time
import streamlit as st
from pydub import AudioSegment
import tempfile
import os
import google.generativeai as genai
import speech_recognition as sr  # For Speech-to-Text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set the Google API key for generative AI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

def summarize_audio(audio_file_path):
    """Summarize the audio using Google's Generative AI."""
    try:
        model = genai.GenerativeModel("models/gemini-2.0-flash-exp")
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


def answer_question(audio_file_path, question, retries=3, delay=5):
    """Answer a question based on the audio content using Google's Generative AI."""
    attempt = 0
    while attempt < retries:
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
            attempt += 1
            if attempt < retries:
                st.warning(f"Attempt {attempt} failed, retrying... ({e})")
                time.sleep(delay)  # Wait before retrying
            else:
                st.error(f"Error during Q&A after {retries} attempts: {str(e)}")
                return None


def speech_to_text():
    """Convert speech to text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        audio = recognizer.listen(source)
    try:
        question_text = recognizer.recognize_google(audio)
        return question_text
    except sr.UnknownValueError:
        st.error("Sorry, I could not understand the audio.")
        return None
    except sr.RequestError:
        st.error("Could not request results from Google Speech Recognition service.")
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


# Streamlit UI
st.markdown("""
<div style="text-align: center;">
    <h1>Welcome to Audix 🎙</h1>
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

# Upload audio files
audio_files = st.file_uploader("Upload Audio Files", type=['wav', 'mp3', 'mp4', 'ogg'], accept_multiple_files=True)

for audio_file in audio_files:
    audio_id = f"audio_{audio_file.name}"
    audio_path = save_uploaded_file(audio_file)
    st.audio(audio_path)

    if audio_id not in st.session_state:
        st.session_state[audio_id] = {"chat_session": [], "summary": None, "is_listening": False, "is_processing_answer": False}

    # Summarize the audio when clicked
    if st.button(f'Summarize Audio', key=f'summarize_{audio_file.name}'):
        with st.spinner(f'Summarizing {audio_file.name}...'):
            summary_text = summarize_audio(audio_path)
            if summary_text:
                st.session_state[audio_id]["summary"] = summary_text
                st.info(summary_text)

    # Display summary if available
    if "summary" in st.session_state[audio_id] and st.session_state[audio_id]["summary"]:
        st.subheader(f"Summary for Audio")
        st.write(st.session_state[audio_id]["summary"])

    # Text input for question
    question = st.text_input(f"Enter your question for audio:", key=f"question_{audio_file.name}")

    # Flag to check if an answer has been generated
    answer_generated = False
    answer_text = None

    # Process the text question when 'Enter' is pressed
    if question and not st.session_state[audio_id]["is_processing_answer"] and not st.session_state[audio_id]["is_listening"]:
        # Immediately set flags to prevent processing old queries
        st.session_state[audio_id]["is_processing_answer"] = True

        with st.spinner(f'Finding answer for audio...'):
            answer_text = answer_question(audio_path, question)
            answer_generated = True

        # Reset the flag after processing
        st.session_state[audio_id]["is_processing_answer"] = False  # Reset flag for new questions

    # Option to ask via voice (directly start listening)
    if st.button(f"Ask with Voice", key=f"voice_{audio_file.name}") and not st.session_state[audio_id]["is_listening"]:
        st.write("Listening for your question... Speak now.")  # Immediately show this message

        # Stop any ongoing processing for voice question
        st.session_state[audio_id]["is_processing_answer"] = False

        # Start the process of listening for speech and processing the question
        st.session_state[audio_id]["is_listening"] = True

        # Convert speech to text (this starts immediately without processing any previous queries)
        question = speech_to_text()

        if question:  # If a question was successfully captured
            with st.spinner(f'Finding answer for audio...'):
                answer_text = answer_question(audio_path, question)
                answer_generated = True
                st.session_state[audio_id]["is_listening"] = False  # End the listening process

    # Reset the flag after processing voice question
    st.session_state[audio_id]["is_listening"] = False

    # Show the confirmation message only once and after processing
    if answer_generated and answer_text:
        st.markdown(f"""
            <div style="background-color: #D3F3D3; color: #25CE25; padding: 10px; border-radius: 5px;">
                <strong>Answer for your question '{question}' has been generated!</strong>
            </div>
        """, unsafe_allow_html=True)

        # Append the question and answer to the chat session history
        st.session_state[audio_id]["chat_session"].append(
            {"role": "user", "text": question})  # User's question
        st.session_state[audio_id]["chat_session"].append(
            {"role": "assistant", "text": answer_text})  # Assistant's answer

    # Display the chat history (User Q&A)
    for message in st.session_state[audio_id]["chat_session"]:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])
