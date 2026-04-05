# DroneMate - Setup and Installation Guide

Detailed instructions on how to install and run the DroneMate AI-Powered Assistant.

## 📋 Prerequisites

To run this application, you must have the following installed on your machine:
- **Python 3.10 or higher**
- **MongoDB Server** (v5.0 or later, running locally)
- **Ollama** (v0.1.20 or later, for local AI functionality)

---

## 🛠️ Installation Steps

### 1. Clone the Project
Navigate to your desired directory and clone the repository.

### 2. Set Up Python Environment
It is highly recommended to use a virtual environment.
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r backend/requirements.txt
```

### 3. Database Configuration
Ensure your MongoDB server is running. You can verify this by checking the connection on `mongodb://localhost:27017` using MongoDB Compass or similar tools.

Seed the database with initial drone knowledge and component data:
```bash
cd backend
python ../data/scripts/seed_database.py
```

### 4. Configure Local AI (Ollama)
If you want to use local AI models, pull the Llama 3 model:
```bash
ollama run llama3
```

Ensure Ollama is running (`ollama serve`) before starting the backend.

### 5. Configure Cloud AI (Backup - Groq/Gemini)
If Ollama is not installed or running, the system will attempt to use cloud failover.
1. Create a `.env` file in the `backend/` directory.
2. Add your API keys:
   ```env
   GROQ_API_KEY=your_groq_key_here
   GEMINI_API_KEY=your_gemini_key_here
   ```

---

## 🚀 Running the Application

Start the FastAPI backend:
```bash
cd backend
python app.py
```

The application will be served at:
- **Frontend**: `http://localhost:8000/`
- **API Documentation**: `http://localhost:8000/docs`

## 🧠 Using the Assistant

- **Chat**: Type questions about drone parts, troubleshooting, and building.
- **Components**: Comparison of thousands of drone parts with real specifications.
- **Guides**: Step-by-step masterclasses for building anything from a 2-inch cinewhoop to a 5-inch racer.
- **Related Topics**: The system will automatically suggest relevant next questions based on your chat context.

---

## 🛑 Troubleshooting

- **MongoDB Connection Error**: Verify that the `MONGO_URI` in `.env` matches your MongoDB connection string.
- **AI Response Fails**: If Ollama and cloud keys are missing, the system will only respond based on its 50+ local knowledge items.
- **Empty UI**: If the components or guides don't load, ensure the backend was seeded correctly using the `seed_database.py` script.
