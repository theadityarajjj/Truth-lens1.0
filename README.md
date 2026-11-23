# 🔎 Truth Lens 1.0

### AI-Powered Fact-Checking & Claim Verification Platform

Truth Lens is an AI-powered fact-checking platform designed to analyse textual statements, extract verifiable claims, retrieve supporting evidence, evaluate source credibility, and generate evidence-based assessments.

The goal is to make information verification more transparent by combining information retrieval, natural language processing, source evaluation, and AI-assisted reasoning.

---

## 🚀 Features

- **Claim Extraction:** Identifies factual claims within submitted text.
- **Evidence Retrieval:** Retrieves relevant information from available sources.
- **Evidence Assessment:** Evaluates retrieved evidence and its relevance to individual claims.
- **AI-Powered Verification:** Uses large language models to assess claims against retrieved evidence.
- **Source Intelligence:** Analyses source credibility, publisher information, and source diversity.
- **Bias Detection:** Identifies potential bias in submitted content.
- **Logical Fallacy Detection:** Analyses statements for potential logical fallacies.
- **Analysis History:** Saves previous investigations for later review.
- **Interactive Dashboard:** Visualises analysis results through charts and analytical metrics.

## 🧠 How It Works

Truth Lens follows a multi-stage verification workflow:

1. **Input:** The user submits a textual statement or passage.
2. **Claim Extraction:** The application identifies individual factual claims.
3. **Evidence Retrieval:** Relevant information is collected from available information sources.
4. **Evidence Processing:** Retrieved information is evaluated and organised.
5. **AI Verification:** The AI analyses the claims using the retrieved evidence.
6. **Intelligence Analysis:** Potential bias and logical fallacies are examined.
7. **Results:** The application presents claim verdicts, evidence, explanations, and source information.
8. **History:** The investigation is saved for future reference.

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Data Visualisation | Chart.js |
| Natural Language Processing | spaCy |
| Machine Learning | scikit-learn |
| AI Integration | Groq, Google Gemini |
| Information Retrieval | Wikipedia API, DuckDuckGo |
| Database | SQLite |
| Data Processing | Pandas |

## 📂 Project Structure

```text
Truth-Lens/
│
├── app.py
├── run.py
├── routes.py
├── requirements.txt
│
├── static/
│   ├── css/
│   ├── js/
│   └── ...
│
├── templates/
│   └── index.html
│
├── .gitignore
├── README.md
└── ...
```

*The structure above illustrates the main application components. Individual filenames and folders may vary.*

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
cd Truth-Lens
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Install the spaCy language model

```bash
python -m spacy download en_core_web_sm
```

### 6. Configure environment variables

Create a `.env` file in the project root and add the API keys required by your configuration.

Example:

```env
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

Never upload your `.env` file or expose your API keys publicly.

### 7. Run the application

```bash
python run.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## 📊 Project Vision

Truth Lens aims to make fact-checking more accessible by combining automated claim extraction, evidence retrieval, source analysis, and AI-assisted reasoning into a single platform.

Rather than relying solely on AI-generated answers, the system attempts to ground its assessments in retrieved evidence and communicate limitations when the available information is insufficient.

## ⚠️ Limitations

- Verification quality depends on the availability and quality of retrieved sources.
- Source credibility scores are heuristic assessments, not guarantees of factual accuracy.
- AI-generated assessments may contain errors.
- Conflicting or insufficient evidence can limit the reliability of a verdict.
- The current version focuses on textual analysis.

## 🔮 Future Scope

Potential improvements include:

- Batch statement analysis.
- Expanded evidence retrieval.
- Improved source independence assessment.
- More advanced claim verification.
- Image and video-based fact-checking.
- Enhanced analytical reporting.

## 👨‍💻 Developer

Developed as an AI-powered fact-checking and information verification project.

**Truth Lens 1.0 — Look beyond the claim. Examine the evidence.**