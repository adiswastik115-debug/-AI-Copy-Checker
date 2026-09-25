import streamlit as st
from PIL import Image
import io
import base64
import requests

# ==========================================
# 1. HUMANIZED SYSTEM PROMPT
# ==========================================
SYSTEM_PROMPT = """
You are a highly experienced, empathetic, and expert CBSE high school teacher grading handwritten exam sheets (Classes 9-12).
You are talking to the student or providing feedback directly.

YOUR HUMAN-LIKE GRADING RULES:
1. HANDWRITING TOLERANCE: Grade like a real human Indian teacher. Students write in all kinds of messy cursive, mixed, or poorly formed handwriting. Try your absolute best to read it. Do not cut marks for minor spelling errors if the answer's phonetic concept is correct, unless it's a dedicated language spelling test.
2. STEP-MARKING: Apply actual CBSE step-marking. Award partial marks for formulas, diagrams, or key equations.
3. NO ARTIFICIAL DECIMAL MARKS: Give realistic marks like 3/5, 3.5/5, 4/5. Do not use microscopic divisions like 3.25/5 or 0.77/5. Keep it natural.
4. TONE: Talk like a supportive, realistic, warm Indian school teacher. Use encouraging words. Speak a natural blend of English or Hinglish (Hindi + English) based on what is asked.
5. CLEAN SUMMARY FORMAT:
   - Total Marks Awarded: [Score/Max]
   - क्या अच्छा लिखा (What went well)
   - कहाँ सुधार की जरूरत है (Areas to improve)
"""

def pil_to_base64_str(img):
    buffered = io.BytesIO()
    img.convert('RGB').save(buffered, format="JPEG", quality=80)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def transcribe_audio(audio_bytes, api_key):
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
    data = {"model": "whisper-large-v3-turbo"}
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        if response.status_code == 200:
            return response.json().get("text", "")
        else:
            st.error(f"STT Error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Voice Connection Failed: {e}")
        return None

def call_groq_api(model, api_key, messages):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    payload = {
        "model": model,
        "messages": payload_messages,
        "temperature": 0.3
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            st.error(f"Groq API Error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Failed to connect: {e}")
        return None

# ==========================================
# 2. STREAMLIT APP UI
# ==========================================
st.set_page_config(page_title="AI Copy Checker", page_icon="👩‍🏫", layout="wide")
st.title("👩‍🏫 CBSE AI Teaching Assistant")
st.markdown("*Easily grade messy handwritten copies and ask follow-up questions via Voice or Text!*")

if "messages" not in st.session_state: st.session_state.messages = []
if "all_images_payload" not in st.session_state: st.session_state.all_images_payload = []
if "last_audio_hash" not in st.session_state: st.session_state.last_audio_hash = None

with st.sidebar:
    st.header("📋 Configuration")
    
    api_key_input = st.text_input("Groq API Key (Optional)", type="password", key="sidebar_key")
    
    # SAFELY GRAB KEY FROM SECRETS (No hardcoded key here!)
    try:
        DEFAULT_API_KEY = st.secrets["GROQ_API_KEY"]
    except:
        DEFAULT_API_KEY = ""
        
    API_KEY = api_key_input if api_key_input else DEFAULT_API_KEY
    
    MODEL_NAME = "qwen/qwen3.8-27b"
    st.info(f"✅ Active Vision Model: **{MODEL_NAME}**")
    
    st.markdown("---")
    st.subheader("📝 Questions & Answers (Optional)")
    question_text = st.text_area("Question(s)", key="q_text_input")
    answer_key = st.text_area("Answer Key / Marking Scheme", key="a_text_input")
    max_marks = st.number_input("Maximum Marks", min_value=1, value=10, key="marks_input")
    
    if st.button("Reset Session 🔄", key="reset_btn"):
        st.session_state.messages = []
        st.session_state.all_images_payload = []
        st.session_state.last_audio_hash = None
        st.rerun()

st.write("### 📸 Upload Materials")
col1, col2, col3 = st.columns(3)

question_images_raw = []
key_images_raw = []
student_images_raw = []

with col1:
    st.markdown("##### 1. Question Paper")
    q_files = st.file_uploader("Upload Questions", type=["jpg", "png"], accept_multiple_files=True, key="q_up")
    if q_files:
        for f in q_files: question_images_raw.append(Image.open(f))
        st.success(f"{len(q_files)} page(s) loaded")

with col2:
    st.markdown("##### 2. Answer Key")
    k_files = st.file_uploader("Upload Answer Key", type=["jpg", "png"], accept_multiple_files=True, key="k_up")
    if k_files:
        for f in k_files: key_images_raw.append(Image.open(f))
        st.success(f"{len(k_files)} page(s) loaded")

with col3:
    st.markdown("##### 3. Student's Copy")
    s_files = st.file_uploader("Upload Answer Sheet", type=["jpg", "png"], accept_multiple_files=True, key="s_up")
    if s_files:
        for f in s_files: student_images_raw.append(Image.open(f))
        st.success(f"{len(s_files)} page(s) ready")

# ==========================================
# 3. EVALUATION
# ==========================================
if len(student_images_raw) > 0 and not st.session_state.messages:
    if st.button("🚀 Evaluate Copy Now", type="primary", key="eval_btn"):
        if not API_KEY:
            st.error("API Key is missing! Please check Streamlit Secrets.")
        else:
            with st.spinner("Analyzing handwriting... Please wait."):
                q_b64s = [pil_to_base64_str(img) for img in question_images_raw]
                k_b64s = [pil_to_base64_str(img) for img in key_images_raw]
                s_b64s = [pil_to_base64_str(img) for img in student_images_raw]
                
                prompt_parts = []
                if question_text: prompt_parts.append(f"Question(s): {question_text}")
                if answer_key: prompt_parts.append(f"Answer Key: {answer_key}")
                prompt_parts.append(f"Max Marks: {max_marks}")
                prompt_parts.append("\nGrade the student's copy attached and give warm constructive feedback.")
                
                initial_prompt = "\n".join(prompt_parts)
                content_payload = [{"type": "text", "text": initial_prompt}]
                
                for q_b64 in q_b64s: content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{q_b64}"}})
                for k_b64 in k_b64s: content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{k_b64}"}})
                for s_b64 in s_b64s: content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{s_b64}"}})
                
                st.session_state.all_images_payload = content_payload
                
                response_text = call_groq_api(MODEL_NAME, API_KEY, [{"role": "user", "content": content_payload}])
                
                if response_text:
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    st.rerun()

# ==========================================
# 4. CHAT & VOICE
# ==========================================
if st.session_state.messages:
    st.markdown("---")
    st.write("### 💬 Discussion & Feedback")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    st.write("---")
    st.write("🎤 **Type or Speak your follow-up feedback:**")
    
    col_text, col_audio = st.columns([3, 2])
    pending_prompt = None
    
    with col_text:
        text_input = st.text_input("Type your question:", key="chat_input")
        if text_input: pending_prompt = text_input
            
    with col_audio:
        recorded_audio = st.audio_input("Record feedback 🎙️", key="mic_input")
        if recorded_audio:
            audio_bytes = recorded_audio.read()
            audio_hash = hash(audio_bytes)
            if st.session_state.last_audio_hash != audio_hash:
                st.session_state.last_audio_hash = audio_hash
                with st.spinner("🎙️ Transcribing..."):
                    transcribed_text = transcribe_audio(audio_bytes, API_KEY)
                    if transcribed_text:
                        st.success(f"You said: \"{transcribed_text}\"")
                        pending_prompt = transcribed_text

    if pending_prompt:
        st.session_state.messages.append({"role": "user", "content": pending_prompt})
        
        api_messages = [{"role": "user", "content": st.session_state.all_images_payload}]
        for msg in st.session_state.messages:
            role = "user" if msg["role"] == "user" else "assistant"
            api_messages.append({"role": role, "content": msg["content"]})
            
        with st.spinner("Thinking..."):
            response_text = call_groq_api(MODEL_NAME, API_KEY, api_messages)
            if response_text:
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.rerun()