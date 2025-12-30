# Streamlit Cloud SQLite fix (safe for local too)
try:
    import pysqlite3
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass  # Local Windows works fine

import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
import time
import hashlib
import sqlite3
import atexit

# ------------------------------------------------------
# Env + API setup
# ------------------------------------------------------
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OWNER_CODE = os.getenv("OWNER_CODE", "")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="StorySmith AI", page_icon="📖")

# ------------------------------------------------------
# SQLite DATABASE SETUP (Email + Password)
# ------------------------------------------------------
DB_FILE = "user_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            credits INTEGER DEFAULT 100,
            last_refill REAL DEFAULT 0,
            stories TEXT DEFAULT '[]',
            created_at REAL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(email, username, password):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO users (email, username, password_hash, credits, last_refill, created_at) 
            VALUES (?, ?, ?, 100, ?, ?)
        """, (email, username, hash_password(password), time.time(), time.time()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(email, password):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user_row = cursor.fetchone()
    
    conn.close()
    
    if user_row and user_row[2] == hash_password(password):
        return {
            "email": user_row[0],
            "username": user_row[1],
            "credits": user_row[3],
            "last_refill": user_row[4],
            "stories": eval(user_row[5]) if user_row[5] else [],
            "created_at": user_row[6]
        }
    return None

def save_user_data(email, data):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET 
            credits = ?, 
            last_refill = ?, 
            stories = ? 
        WHERE email = ?
    """, (data["credits"], data["last_refill"], str(data["stories"]), email))
    conn.commit()
    conn.close()

def refill_user_credits(user_data):
    now = time.time()
    elapsed_minutes = (now - user_data["last_refill"]) / 60
    if elapsed_minutes > 0:
        gained = int(elapsed_minutes * 2)
        user_data["credits"] = min(100, user_data["credits"] + gained)
        user_data["last_refill"] = now
        return True
    return False

# ------------------------------------------------------
# MAX MODELS
# ------------------------------------------------------
MODEL_LIST = [
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.5-flash-lite-preview-09-2025",
    "models/gemini-2.5-flash",
    "models/gemini-2.5-flash-preview-09-2025", 
    "models/gemini-2.0-flash-lite",
    "models/gemini-2.0-flash-lite-001",
    "models/gemini-2.0-flash",
    "models/gemini-2.0-flash-exp",
    "models/gemini-2.0-flash-001",
    "models/gemini-flash-latest",
    "models/gemini-flash-lite-latest",
]

def generate_with_fallback(prompt_text: str, temperature: float = 0.7, user_id: str = ""):
    for model_name in MODEL_LIST:
        try:
            m = genai.GenerativeModel(
                model_name,
                generation_config={"temperature": temperature}
            )
            response = m.generate_content(prompt_text)
            return response.text, model_name.split("/")[-1]
        except:
            time.sleep(0.5)
            continue
    raise Exception("Generation temporarily unavailable")

# ------------------------------------------------------
# AUTH SYSTEM (Email + Password)
# ------------------------------------------------------
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

# AUTH SCREEN
if not st.session_state.current_user:
    st.title("👋 Welcome to StorySmith AI")
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        st.markdown("### Login with Email")
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password")
        
        if st.button("🚀 Login"):
            if email and password:
                user_data = authenticate_user(email, password)
                if user_data:
                    st.session_state.user_email = email
                    st.session_state.current_user = user_data["username"]
                    st.session_state.user_data = user_data
                    st.success(f"✅ Welcome back, {user_data['username']}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid email or password")
            else:
                st.warning("👆 Enter email and password")
    
    with tab2:
        st.markdown("### Create New Account")
        new_email = st.text_input("Email", key="reg_email", placeholder="your.email@example.com")
        new_username = st.text_input("Username", key="reg_username")
        new_password = st.text_input("Password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        if st.button("📝 Register"):
            if new_email and new_username and new_password and confirm_password:
                if new_password != confirm_password:
                    st.error("❌ Passwords don't match")
                elif register_user(new_email, new_username, new_password):
                    st.success(f"✅ Account created for {new_username}!")
                    st.info("🔄 Switch to Login tab and sign in")
                else:
                    st.error("❌ Email already exists")
            else:
                st.warning("👆 Fill all fields")
    
    st.stop()

# USER DASHBOARD
current_user = st.session_state.current_user
user_email = st.session_state.user_email
user_data = st.session_state.user_data

# Initialize session data
if "story_text" not in user_data:
    user_data["story_text"] = ""
if "story_model" not in user_data:
    user_data["story_model"] = ""
if "prompt" not in user_data:
    user_data["prompt"] = ""

# ------------------------------------------------------
# UI (PER-USER)
# ------------------------------------------------------
st.sidebar.markdown(f"👤 **{current_user}**")
st.sidebar.markdown(f"📧 **{user_email}**")
st.sidebar.markdown(f"💰 **Credits:** {user_data['credits']}")

# LOGOUT
if st.sidebar.button("🚪 Logout"):
    st.session_state.current_user = None
    st.session_state.user_email = None
    st.session_state.user_data = {}
    st.rerun()

# ADMIN PANEL
if st.sidebar.checkbox("🔐 Admin Panel"):
    admin_code = st.sidebar.text_input("Admin code", type="password")
    if admin_code == OWNER_CODE:
        user_data["credits"] = 1000
        save_user_data(user_email, user_data)
        st.sidebar.success("✨ Admin mode")

st.sidebar.header("⚙️ Story Settings")
genre = st.sidebar.selectbox("Genre", ["Any", "Fantasy", "Sci-Fi", "Adventure", "Mystery", "Horror", "Romance"])
length = st.sidebar.slider("Word count", 200, 800, 400)
temperature = st.sidebar.slider("Creativity", 0.1, 1.0, 0.7)

refill_user_credits(user_data)
save_user_data(user_email, user_data)

# QUICK PRESETS
st.markdown("### 🚀 Quick Stories")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🤖 Robot Adventure"):
        user_data["prompt"] = "a robot exploring alien planets"
        st.rerun()
with col2:
    if st.button("🪄 Magic School"):
        user_data["prompt"] = "a young wizard at magic school"
        st.rerun()
with col3:
    if st.button("⏳ Time Travel"):
        user_data["prompt"] = "scientist invents time machine"
        st.rerun()

prompt = st.text_input(
    "Enter your story idea:",
    value=user_data["prompt"],
    placeholder="e.g., 'a brave robot exploring alien planets'"
)

# GENERATE
if st.button("✨ Generate New Story", type="primary"):
    if not prompt:
        st.warning("👆 Enter a story idea above!")
    elif user_data["credits"] <= 0:
        st.warning("❌ Not enough credits.")
    else:
        estimated_chars = int(length * 6)
        story_cost = max(1, int(estimated_chars * 0.02))

        if user_data["credits"] < story_cost:
            st.warning(f"❌ Not enough credits. Needed {story_cost}, have {user_data['credits']}.")
        else:
            with st.spinner("✍️ Writing your story..."):
                user_data["story_text"] = ""
                user_data["story_model"] = ""
                
                story_prompt = f"""
Write a complete short story (about {length} words) about: "{prompt}"

Genre: {genre}
Creativity: {temperature}

Requirements:
- Engaging hook in first paragraph
- Clear beginning, middle, climax, resolution
- Vivid descriptions and interesting characters
- Fun and immersive tone

Format: Clean prose only.
"""

                try:
                    story_text, used_model = generate_with_fallback(story_prompt, temperature)
                    user_data["credits"] = max(0, user_data["credits"] - story_cost)
                    user_data["story_text"] = story_text
                    user_data["story_model"] = used_model
                    user_data["stories"].append({
                        "prompt": prompt,
                        "story": story_text,
                        "model": used_model,
                        "genre": genre,
                        "length": length,
                        "timestamp": time.time()
                    })
                    
                    save_user_data(user_email, user_data)

                    st.success(f"✅ Story generated using {used_model}! Cost: {story_cost} credits.")
                    st.rerun()
                except Exception as e:
                    st.error("Generation temporarily unavailable.")

# SHOW STORY
if user_data["story_text"]:
    st.markdown("## 📚 Your Story")
    st.markdown(user_data["story_text"])
    
    col1, col2 = st.columns([3, 1])
    with col2:
        st.download_button(
            "💾 Download",
            data=user_data["story_text"],
            file_name=f"{current_user}_story_{int(time.time())}.txt",
            mime="text/plain"
        )
    
    word_count = len(user_data["story_text"].split())
    st.caption(f"By {user_data['story_model']} | {word_count} words")

if user_data["prompt"]:
    st.caption(f"Prompt: '{user_data['prompt']}'")
