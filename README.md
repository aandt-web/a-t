# Lingua Flow

> **AI-powered PDF and Audio Transformer**  
> Convert PDFs into speech, translate text into multiple languages, and process audio seamlessly, all in one place.


---

## Introduction

Lingua Flow is a simple but powerful system that transforms documents and audio into accessible formats.  
It was designed to help students, researchers, and everyday users quickly:

- Extract text from **PDFs**
- Translate that text into multiple languages
- Convert text into **natural speech**
- Process audio files and generate translations

This project is open-source and built to be extended by the community.

---

## Features

- **PDF Processing**
  - Extract text from digital and scanned PDFs
  - Handle multiple pages with stability
  - Error messages for corrupted files

- **Translation**
  - Powered by Google Translator (via `deep-translator`)
  - Supports over 20+ languages
  - Automatic detection of source language

- **Text-to-Speech (TTS)**
  - Uses `gTTS`
  - Generates `.mp3` audio
  - Adjustable speed and tone

- **Audio-to-Text**
  - Speech recognition for `.wav`, `.mp3`, `.flac`
  - Converts voice to text with accuracy
  - Background noise handling

- **Integration**
  - Flask web interface
  - JSON REST API endpoints
  - Docker container support

---

## How It Works

1. User uploads **PDF** or **Audio** file.  
2. System extracts **text** (via OCR or speech recognition).  
3. Text is passed into **translation module**.  
4. User selects target language.  
5. Text is converted into **speech** and output as `.mp3`.  
6. User downloads results.

---

## Technology Stack

- **Backend**: Python + Flask  
- **OCR & PDF Handling**: PyPDF2  
- **Translation**: Deep Translator  
- **TTS**: gTTS  
- **Audio Processing**: SpeechRecognition + pydub + ffmpeg  
- **Frontend**: HTML, CSS (Jinja2 templates)  
- **Deployment**: Render + Docker  

---

## Live Demo (Render Hosting)

Lingua Flow is deployed publicly using **Render**.  

- **Base URL**: [https://lingua-flow.onrender.com/](https://lingua-flow.onrender.com/)  

When you open the URL in your browser, you’ll see the **web interface** where you can upload PDFs or audio files and get translations + speech outputs.

---

### Available Routes

| Route                     | Description |
|----------------------------|-------------|
| `/`                        | Home page (upload form) |
| `/upload/pdf` (POST)       | Upload a PDF file for text extraction + translation |
| `/upload/audio` (POST)     | Upload an audio file for speech-to-text + translation |
| `/result/<id>` (GET)       | Get processed results by task ID |
| `/health` (GET)            | Check if the API/server is running |

---

### Example Usages

- **Open Web Interface**  
  Go to [https://lingua-flow.onrender.com/](https://lingua-flow.onrender.com/)  
  → Upload `sample.pdf` → Choose language → Download `.mp3`.

- **API Request (PDF Upload)**  

```bash
curl -X POST -F "file=@document.pdf" https://lingua-flow.onrender.com/upload/pdf

