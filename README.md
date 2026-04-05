# DroneMate

DroneMate is an intelligent, full-stack AI assistant designed to help drone enthusiasts with building, troubleshooting, and learning about FPV drones. It combines a curated local knowledge base and component database with advanced AI models for a seamless, high-tech experience.

## ✨ Features

- **🧠 Hybrid AI Assistant**: Searches a 50+ entry local knowledge base before failing over to local (Ollama) or cloud (Groq/Gemini) AI models.
- **🛠️ Component Database**: Interactive directory of drone parts with specifications, compatibility checks, and ratings.
- **📑 Build Guides**: Step-by-step masterclasses for building different types of drones (Racing, Freestyle, etc.).
- **💬 Persistent Chat**: Session-based conversation history stored in MongoDB.
- **⚡ Modern UI**: A sleek, high-contrast dark mode interface built with Tailwind CSS and Vanilla JavaScript.

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **MongoDB** (running on localhost:27017)
- **Ollama** (optional but recommended for local AI)

### Installation

1. **Clone and Setup**
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file in the `backend/` directory based on `.env.example`.
   ```env
   GROQ_API_KEY=your_key_here
   ```

3. **Seed the Database**
   ```bash
   cd backend
   python ../data/scripts/seed_database.py
   ```

4. **Run the Application**
   ```bash
   python app.py
   ```
   The app will be available at `http://localhost:8000`.

## 📂 Project Structure

- `backend/`: FastAPI application, routes, and AI logic.
- `frontend/`: Single-page application and static assets.
- `data/`: Seed data and database management scripts.
- `docs/`: Detailed API and setup documentation.

## 🛠️ Technology Stack

- **Backend**: FastAPI, Motor (Async MongoDB), Pydantic
- **Database**: MongoDB
- **AI**: Ollama (Local), Groq (Llama 3 Cloud), Gemini Pro
- **Frontend**: Tailwind CSS, Vanilla JS, Font Awesome

---
Designed with ❤️ for the FPV community.
