 SocrAI Advanced Tutor (v2)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Active-success)

> **SocrAI Advanced Tutor (v2)** is an AI-powered **Socratic Dialogue Learning Platform** built using **Streamlit** and **FastAPI**.  
> It helps learners explore deeper reasoning, ethics, and philosophy by engaging in reflective, question-driven conversations with an AI tutor.

---

## 🧩 Overview

The Socratic method is the art of learning through questioning — *not by memorizing*.  
**SocrAI** replicates this timeless teaching approach with artificial intelligence.

It can:
- 🧠 Ask deep, reasoning-based questions
- 🗣️ Engage in natural conversation
- 🧩 Allow persona customization (Socrates / Friendly / Direct)
- ⚙️ Run locally via Streamlit or deploy to the cloud
- 🧱 Extend with FastAPI endpoints for backend AI logic

---

## 🧰 Tech Stack

| Layer | Technology |
|--------|-------------|
| **Frontend** | Streamlit |
| **Backend** | FastAPI |
| **Language** | Python 3.10+ |
| **AI Model** | OpenAI GPT (3.5 / 4.0) |
| **Deployment** | Streamlit Cloud / Docker / Render |
| **Libraries** | `streamlit`, `fastapi`, `openai`, `pydantic`, `requests`, `uvicorn` |

---

## ⚙️ Installation Guide

### 1️⃣ Prerequisites
- Python **3.10 or newer**
- `pip` package manager
- Valid **OpenAI API key**
- (Optional) Docker

---

### 2️⃣ Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/SocrAI-Advanced-Tutor.git
cd SocrAI-Advanced-Tutor
3️⃣ Create Virtual Environment
bash
Copy code
python -m venv .venv
Activate:

Windows (PowerShell)

powershell
Copy code
.venv\Scripts\Activate.ps1
macOS / Linux

bash
Copy code
source .venv/bin/activate
4️⃣ Install Dependencies
bash
Copy code
pip install -r requirements.txt
5️⃣ Run the Application
bash
Copy code
streamlit run socratic_tutor_advanced_v2.py
Visit → http://localhost:8501

🧠 How to Use
Open the Streamlit app.

Enter your OpenAI API Key (kept private).

Choose your Tutor Persona:

Socrates 🏛️ (Philosophical)

Friendly 👋 (Casual)

Direct 🎯 (Critical Thinking)

Select Dialogue Style: Gentle / Neutral / Critical.

Enter a Topic and your Response.

Click Start Dialogue to begin the AI conversation.

💬 Example Dialogue
Topic: What is virtue?
Student: Virtue means doing what is good.
SocrAI (Socrates persona): Interesting. But what defines "good"? Is virtue something taught or innate?

🗂️ Folder Structure
bash
Copy code
SocrAI-Advanced-Tutor/
│
├── socratic_tutor_advanced_v2.py        # Main Streamlit App
├── requirements.txt                     # Dependencies
├── Dockerfile                           # For container deployment
├── .gitignore                           # Ignore venv/cache/files
└── README.md                            # Project documentation
🧱 requirements.txt
nginx
Copy code
streamlit
requests
openai
fastapi
uvicorn
pydantic
🐳 Docker Deployment
Build Image
bash
Copy code
docker build -t socrai-tutor .
Run Container
bash
Copy code
docker run -p 8501:8501 socrai-tutor
Dockerfile

dockerfile
Copy code
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["streamlit", "run", "socratic_tutor_advanced_v2.py", "--server.port=8501", "--server.address=0.0.0.0"]
🔌 API Endpoints (FastAPI Module)
Method	Endpoint	Description
POST	/api/dialogue	Generate AI tutor response
GET	/api/trace	View reasoning trace
GET	/api/summary	Get dialogue summary
POST	/api/extract_terms	Extract key phrases

Example cURL

bash
Copy code
curl -X POST "http://localhost:8000/api/dialogue" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode":"Gentle","persona":"Socrates","topic":"What is justice?","student_text":"Justice is fairness."}'
⚙️ Troubleshooting
Issue	Solution
streamlit: command not found	Install Streamlit: pip install streamlit
Blank UI	Reload page or clear cache
Invalid API Key	Re-enter valid OpenAI key (starts with sk-)
Port already in use	Use --server.port 8502
Slow responses	Try smaller OpenAI model or check network speed

🔒 Security Tips
Never share or upload your OpenAI API key to GitHub.

Use .env or .streamlit/secrets.toml for key storage.

Enable HTTPS if deploying publicly.

Use FastAPI middleware for rate limiting and access control in production.

🧭 Roadmap
 Add persistent dialogue saving

 Multi-language support

 Voice conversation mode

 Enhanced concept mapping

 Tutor analytics dashboard

 Async model execution

🧰 Maintenance Commands
bash
Copy code
# Update dependencies
pip install -U -r requirements.txt

# Export current environment
pip freeze > requirements.txt
📜 License
Licensed under the MIT License — free to use, modify, and share with attribution.
© 2025 Vinay Kumar

👨‍💻 Author
Vinay Kumar
AI Systems & Electronics Enthusiast
📧 [Add your email or GitHub profile]
🌐 GitHub: https://github.com/YOUR_USERNAME

“The greatest learning begins not with answers — but with the right questions.”
— SocrAI Advanced Tutor (v2)

yaml
Copy code

---

✅ **How to Upload This README:**
1. Open your project folder.  
2. Create a new file named `README.md`.  
3. Copy-paste the above text into it.  
4. Save the file.  
5. Run the following commands:
   ```bash
   git add README.md
   git commit -m "Added professional README.md"
   git push
Refresh your GitHub repository — it will render perfectly formatted.
