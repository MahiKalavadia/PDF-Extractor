# PDF EXTRACTOR using LLM Call and Groq API


## Setup & Run Locally

### 1. Clone the repo

```bash
git clone https://github.com/MahiKalavadia/PDF-Extractor
```

### 2. Create and activate virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---
#### Create Groq API Key

### 1. Create Account
Open Groq and create your account
Groq link: 
https://groq.com

### 2. Create API key

Copy the API key generated

----

#### Set environment variables

Create a `.env` file:

```
GROQ_API_KEY=your_groq_api_key
```
#### Run the backend

```bash
uvicorn main:app --reload
```

#### Open to use

http://127.0.0.1:8000/docs