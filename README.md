# AI Story Generator (Streamlit + Google Gemini)
**Live Demo:** [Click here to try the app](https://storysmith-ai-en4jvvx6duaq28gmuantnh.streamlit.app/)

AI Story Generator is a web app that lets users sign up, log in, and generate complete short stories from simple prompts using Google Gemini models. It includes authentication, a credit system, and persistent storage using SQLite.

## Features

- **User accounts**
  - Email/password registration and login using Streamlit forms.
  - Passwords stored as SHA-256 hashes in a local SQLite database.

- **Credits and limits**
  - Each story generation consumes credits based on requested word count. 
  - Automatic credit refill: 2 credits per minute, up to a maximum of 100 credits per user.

- **Admin panel**
  - Optional admin mode protected by an `OWNER_CODE` environment variable.
  - Admin can boost a user’s credits (e.g., to 1000) for testing or demos.  

- **AI story generation**
  - Uses Google Gemini via the `google-generativeai` Python SDK.
  - Fallback across multiple Gemini Flash / 2.x models for more reliable generation.
  - Prompt enforces clear structure (beginning, middle, climax, resolution) and engaging tone.

- **Story controls & UX**
  - Genre selection: Any, Fantasy, Sci‑Fi, Adventure, Mystery, Horror, Romance.
  - Word count slider (200–800 words) and creativity (temperature) slider. 
  - Quick preset prompts (robot adventure, magic school, time travel). 
  - Story displayed in the app with model name and word count, plus download as `.txt`.
## Tech Stack

- **Framework:** Streamlit  
- **Language:** Python  
- **AI / LLM:** Google Gemini via `google-generativeai`  
- **Database:** SQLite (`user_database.db`) for users, credits, and stories.
- **Config:** `python-dotenv` for `GOOGLE_API_KEY` and `OWNER_CODE` environment variables.

