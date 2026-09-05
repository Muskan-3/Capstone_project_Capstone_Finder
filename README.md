# 🔎 ProjectLens

### Discovering Projects That Truly Fit

ProjectLens is a full-stack project recommendation system that helps students discover **final-year capstone projects** based on their skills and interests.

🌐 **Live Demo:** https://capstone-project-capstone-finder.vercel.app/

## ✨ Features

* 🎯 Personalized project recommendations
* 🧠 Machine Learning based matching
* 📊 Real project match scores
* 🔀 Diverse recommendations
* ⚠️ Honest low-confidence results when there is no strong match
* 📌 Recommendations are based on real project data
* 🛠️ Admin panel for managing projects and retraining the model

## 🤖 How It Works

```text
Student Skills & Interests
          ↓
       TF-IDF
          ↓
   KMeans Clustering
          ↓
  Cosine Similarity
          ↓
   Project Ranking
          ↓
 MMR Diversification
          ↓
   Best-Fit Projects
```

ProjectLens uses **TF-IDF, KMeans, Cosine Similarity, and MMR** to find projects that best match a student's profile.

The system is **fully offline** and does not use OpenAI, Anthropic, or any external LLM/inference API.

## 🛠️ Tech Stack

**Frontend:** Next.js 14, TypeScript, Tailwind CSS

**Backend:** FastAPI, Python, SQLite

**Machine Learning:** Scikit-learn, TF-IDF, KMeans, Cosine Similarity, MMR

## 📂 Project Structure

```text
FinalYearCapstoneProject/
├── backend/     FastAPI + SQLite + ML pipeline
└── frontend/    Next.js 14 + TypeScript + Tailwind
```

## 🚀 Run Locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

## 🎯 Why ProjectLens?

Choosing the right final-year project can be difficult. ProjectLens helps students find projects that match their **skills, interests, and project scope**.

> **Don't just discover projects. Discover projects that truly fit.**

## 👩‍💻 Author

**Muskan**

GitHub: https://github.com/Muskan-3
