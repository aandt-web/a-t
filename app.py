import logging
import time
import sys
import os
from flask import Flask, request, send_file, jsonify, after_this_request
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
from gtts import gTTS
import tempfile
from deep_translator import GoogleTranslator
import speech_recognition as sr
import pydub

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, filename='app.log')

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 5000  # Character limit for text processing
MAX_REQUEST_CHARS = 5000  # Character limit for translation requests

# Global variable declaration
USE_GOOGLE_CLOUD = True  # Default to True if google-cloud-translate is installed
translate_client = None  # Will be initialized lazily

try:
    import google.cloud.translate_v2 as translate
except ImportError:
    logging.warning("Google Cloud Translate not found. Falling back to deep-translator.")
    USE_GOOGLE_CLOUD = False

# Check for speech_recognition availability
HAS_STT = True
VALID_STT_LANGS = []
try:
    import speech_recognition as sr
    VALID_STT_LANGS = ['en-US', 'fr-FR', 'es-ES', 'de-DE', 'my-MM']  # Supported STT languages
except ImportError:
    logging.warning("SpeechRecognition not found or incompatible. STT functionality disabled.")
    HAS_STT = False
    sr = None

# Helper functions
def check_file_size(file):
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer to the beginning
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds the limit of {MAX_FILE_SIZE / (1024 * 1024)}MB")

def extract_text_from_pdf(pdf_file) -> str:
    try:
        check_file_size(pdf_file)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]
            logging.warning(f"PDF text truncated to {MAX_TEXT_LENGTH} characters.")
        return text
    except PdfReadError as e:
        raise ValueError(f"Failed to read PDF: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error extracting text from PDF: {str(e)}")

def tts_to_tempfile(text: str, lang: str) -> str:
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_file.name)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        raise ValueError(f"Text-to-speech conversion failed: {str(e)}")

def convert_to_wav(audio_file) -> str:
    try:
        check_file_size(audio_file)
        temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix="." + audio_file.filename.split(".")[-1])
        audio_file.save(temp_audio_path.name)
        temp_audio_path.close()

        audio = pydub.AudioSegment.from_file(temp_audio_path.name)
        wav_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        audio.export(wav_path, format="wav")
        os.unlink(temp_audio_path.name)
        return wav_path
    except Exception as e:
        raise ValueError(f"Audio conversion failed: {str(e)}")

def validate_stt_lang(lang: str) -> str:
    if lang not in VALID_STT_LANGS:
        logging.warning(f"Unsupported STT language '{lang}'. Falling back to 'en-US'.")
        return 'en-US'
    return lang

def stt_google(audio_path: str, language: str = 'en-US') -> str:
    if not HAS_STT:
        raise ValueError("Speech-to-Text functionality is disabled.")
    language = validate_stt_lang(language)
    recognizer = sr.Recognizer()
    wav_path = convert_to_wav(audio_path) # Use convert_to_wav here
    try:
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language=language)
    except sr.UnknownValueError:
        raise ValueError("Could not understand the audio.")
    except sr.RequestError as e:
        raise ValueError(f"Speech service error: {e}")
    finally:
        try:
            os.unlink(wav_path)
        except Exception as e:
            logging.error(f"Failed to delete temp file {wav_path}: {e}")

def get_translate_client():
    global translate_client

    if not USE_GOOGLE_CLOUD:
        return None
    if translate_client is None:
        try:
            import google.auth
            from google.cloud import translate_v2
            credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            if not credentials_json:
                logging.error("GOOGLE_APPLICATION_CREDENTIALS_JSON not set. Falling back to deep-translator.")

                USE_GOOGLE_CLOUD = False
                return None
            import json
            credentials = google.auth.credentials.Credentials.from_service_account_info(json.loads(credentials_json))
            translate_client = translate_v2.Client(credentials=credentials)
        except Exception as e:
            logging.error(f"Failed to initialize Google Translate client: {e}")
            USE_GOOGLE_CLOUD = False
            return None
    return translate_client

def translate_batch_text(text: str, target_lang: str) -> str:
    try:
        chunks = [text[i:i + MAX_REQUEST_CHARS] for i in range(0, len(text), MAX_REQUEST_CHARS)]
        if USE_GOOGLE_CLOUD:
            client = get_translate_client()
            if client:
                translated_chunks = client.translate(chunks, target_language=target_lang)
                return " ".join([result['translatedText'] for result in translated_chunks])
        translated_chunks = [GoogleTranslator(source='auto', target=target_lang).translate(chunk) for chunk in chunks]
        return " ".join(translated_chunks)
    except Exception as e:
        logging.error(f"Translation Error: {e}")
        raise ValueError(f"Translation failed: {str(e)}")

# HTML content (corrected and completed JavaScript)
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Lingua Flow – Transform Documents & Audio with AI</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            brand: {
              50: '#f5f3ff',
              100: '#ede9fe',
              200: '#ddd6fe',
              300: '#c4b5fd',
              400: '#a78bfa',
              500: '#8b5cf6',
              600: '#7c3aed',
              700: '#6b21a8',
              800: '#581c87',
              900: '#3b0764'
            },
            ink: {
              100: '#E6ECEF',
              200: '#C9D4DA',
              300: '#A0AEC0',
              400: '#94A3B8',
              700: '#1F2937',
              900: '#0B1020'
            }
          },
          boxShadow: {
           glass: '0 10px 30px rgba(0,0,0,.35)'         },
          backdropBlur: {
            xs: '2px'
          }
        }
      }
    };
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-start: #0f172a;
      --bg-end: #111827;
      --grad-1: #1A1A2E;
      --grad-2: #16213E;
      --logo-grad-1: #6B46C1;
      --logo-grad-2: #4C51BF;
    }
    html, body { height: 100% }
    body { font-family: 'Inter', system-ui, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
    .animated-bg {
      background: linear-gradient(120deg, var(--grad-1), var(--grad-2));
      background-size: 400% 400%;
      animation: gradientShift 18s ease infinite;
    }
    @keyframes gradientShift { 0% { background-position: 0% 50% } 50% { background-position: 100% 50% } 100% { background-position: 0% 50% } }
    .glass { background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.08); }
    .btn-primary { background: linear-gradient(90deg, var(--logo-grad-1), var(--logo-grad-2)); }
    .btn-primary:hover { filter: brightness(1.1) }
    .brand-chip { background: linear-gradient(90deg, var(--logo-grad-1), var(--logo-grad-2)); }
  </style>
</head>
<body class="animated-bg min-h-screen text-slate-100 flex flex-col">
  <header class="w-full">
    <div class="mx-auto max-w-6xl px-4 py-5 flex items-center justify-between">
      <a href="#" class="flex items-center gap-3 group">
        <img src="/static/logo.png" alt="Logo" class="h-11 w-11 object-contain">
        <div>
          <div class="text-xl font-extrabold tracking-tight leading-5">Lingua Flow</div>
          <div class="text-xs text-slate-300/80 -mt-0.5">Transform • Translate • Speak</div>
        </div>
      </a>
      <div class="hidden md:flex items-center gap-2">
        <span class="brand-chip text-xs font-semibold text-white px-3 py-1.5 rounded-full shadow">AI Powered</span>
        <span class="text-sm text-slate-300">5+ Languages</span>
      </div>
    </div>
  </header>
  <section class="mx-auto max-w-6xl px-4 pb-6">
    <div class="grid lg:grid-cols-2 gap-6 items-stretch">
      <div class="glass rounded-2xl shadow-glass p-6 md:p-8 flex flex-col justify-center">
        <h1 class="text-3xl md:text-4xl font-extrabold leading-tight">
          Transform documents & audio with
          <span class="bg-clip-text text-transparent" style="background-image:linear-gradient(90deg, var(--logo-grad-1), var(--logo-grad-2))">real‑time AI</span>
        </h1>
        <p class="mt-3 text-slate-200/90">Extract, translate, and convert between text and speech in a single, elegant tool. Fast. Accurate. Private.</p>
        <ul class="mt-5 space-y-2 text-sm text-slate-200/90">
          <li class="flex items-start gap-3">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mt-0.5 text-brand-300">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
            PDF text extraction with OCR-ready pipeline
          </li>
          <li class="flex items-start gap-3">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mt-0.5 text-brand-300">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
            Multi‑language translation
          </li>
          <li class="flex items-start gap-3">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mt-0.5 text-brand-300">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
            Natural‑sounding text‑to‑speech
          </li>
          <li class="flex items-start gap-3" style="%(stt_disabled)s">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mt-0.5 text-brand-300">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
            Accurate speech recognition
          </li>
        </ul>
      </div>
      <div class="glass rounded-2xl shadow-glass p-6 md:p-8">
        <form id="toolForm" class="space-y-5" enctype="multipart/form-data">
          <div>
            <label class="block text-sm font-semibold mb-2" for="mode">Processing Mode</label>
            <div class="relative">
              <select id="mode" name="mode" class="w-full appearance-none rounded-xl bg-slate-900/60 border border-white/10 px-4 py-3 pr-10 focus:outline-none focus:ring-2 focus:ring-brand-400">
                <option value="pdf_audio">PDF → Audio • Convert PDF text to speech</option>
                <option value="pdf_translate">PDF → Translate • Extract & translate text</option>
                <option value="pdf_translate_audio">PDF → Translate → Audio • Translate then speech</option>
                %(stt_options)s
              </select>
              <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-4">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-slate-300"><path d="M6 9l6 6 6-6"/></svg>
              </div>
            </div>
          </div>
          <div id="langDiv">
            <label class="block text-sm font-semibold mb-2" for="lang">Target Language</label>
            <div class="relative">
              <select id="lang" name="lang" class="w-full appearance-none rounded-xl bg-slate-900/60 border border-white/10 px-4 py-3 pr-10 focus:outline-none focus:ring-2 focus:ring-brand-400">
                <option value="en">English</option>
                <option value="my">Myanmar</option>
                <option value="fr">French</option>
                <option value="es">Spanish</option>
                <option value="de">German</option>
              </select>
              <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-4">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-slate-300"><path d="M6 9l6 6 6-6"/></svg>
              </div>
            </div>
          </div>
          <div id="pdfInput">
            <label class="block text-sm font-semibold mb-2" for="pdf">1. Upload PDF</label>
            <label class="group flex items-center justify-between gap-4 rounded-xl border border-dashed border-white/15 bg-slate-900/50 p-4 hover:border-brand-300 cursor-pointer">
              <div class="flex items-center gap-3">
                <div class="rounded-lg p-2" style="background:linear-gradient(90deg, var(--logo-grad-1), var(--logo-grad-2))">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                </div>
                <div>
                  <div class="text-sm font-semibold">Drag & drop your PDF here</div>
                  <div class="text-xs text-slate-300">or click to browse • Max 10MB</div>
                </div>
              </div>
              <input id="pdf" name="pdf" type="file" accept="application/pdf" class="sr-only" />
              <span id="pdfName" class="text-xs text-slate-300">No file chosen</span>
            </label>
          </div>
          <div id="audioInput" class="hidden">
            <label class="block text-sm font-semibold mb-2" for="audio">1. Upload Audio</label>
            <label class="group flex items-center justify-between gap-4 rounded-xl border border-dashed border-white/15 bg-slate-900/50 p-4 hover:border-brand-300 cursor-pointer">
              <div class="flex items-center gap-3">
                <div class="rounded-lg p-2" style="background:linear-gradient(90deg, var(--logo-grad-1), var(--logo-grad-2))">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M12 1v11"/><path d="M5 10a7 7 0 0 0 14 0"/><path d="M8 21h8"/></svg>
                </div>
                <div>
                  <div class="text-sm font-semibold">Drag & drop your audio</div>
                  <div class="text-xs text-slate-300">MP3, WAV, M4A, OGG • Max 10MB</div>
                </div>
              </div>
              <input id="audio" name="audio" type="file" accept="audio/*" class="sr-only" />
              <span id="audioName" class="text-xs text-slate-300">No file chosen</span>
            </label>
          </div>
          <div id="sttLangRow" class="hidden">
            <label for="stt_lang" class="block text-sm font-semibold mb-2">Speech Language (for STT)</label>
            <input id="stt_lang" name="stt_lang" type="text" value="en-US" placeholder="e.g., en-US, fr-FR" class="w-full rounded-xl bg-slate-900/60 border border-white/10 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-400"/>
          </div>
          <button type="submit" class="btn-primary w-full rounded-xl py-3.5 font-semibold text-white shadow-lg active:scale-[.99] transition">2. Start Processing</button>
          <div id="progressWrap" class="hidden h-2 w-full overflow-hidden rounded bg-white/10">
            <div class="h-full w-0 bg-white/60 animate-[loader_2s_ease_infinite]"></div>
          </div>
          <style>
            @keyframes loader { 0% { width: 0 } 50% { width: 80% } 100% { width: 100% } }
          </style>
          <div class="space-y-3 pt-2">
            <audio id="player" class="hidden w-full" controls></audio>
            <textarea id="outputText" class="hidden w-full min-h-[140px] rounded-xl bg-slate-900/60 border border-white/10 p-3 text-sm" placeholder="Results will appear here"></textarea>
          </div>
        </form>
      </div>
    </div>
  </section>
  <section class="mx-auto max-w-6xl px-4 pb-10">
    <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="glass rounded-xl p-4 flex items-start gap-3">
        <div class="rounded-md p-2" style="background:linear-gradient(90deg, var(--logo-grad-1), var(--logo-grad-2))">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
        </div>
        <div>
          <div class="font-semibold">PDF Extraction</div>
          <div class="text-xs text-slate-300">Pull clean text from complex PDFs.</div>
        </div>
      </div>
      <div class="glass rounded-xl p-4 flex items-start gap-3">
        <div class="rounded-md p-2" style="background:linear-gradient(90deg, var(--logo-grad-1), var(--logo-grad-2))">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg>
        </div>
        <div>
          <div class="font-semibold">Translate</div>
          <div class="text-xs text-slate-300">20+ languages, auto‑detect.</div>
        </div>
      </div>
      <div class="glass rounded-xl p-4 flex items-start gap-3">
        <div class="rounded-md p-2" style="background:linear-gradient(90deg, var(--logo-grad-1), var(--logo-grad-2))">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M12 1v11"/><path d="M5 10a7 7 0 0 0 14 0"/><path d="M8 21h8"/></svg>
        </div>
        <div>
          <div class="font-semibold">Text‑to‑Speech</div>
          <div class="text-xs text-slate-300">Natural voices, quick output.</div>
        </div>
      </div>
      <div class="glass rounded-xl p-4 flex items-start gap-3" style="%(stt_disabled)s">
        <div class="rounded-md p-2" style="background:linear-gradient(90deg, var(--logo-grad-1), var(--logo-grad-2))">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M12 5v6"/><rect x="9" y="11" width="6" height="8" rx="2"/></svg>
        </div>
        <div>
          <div class="font-semibold">Speech‑to‑Text</div>
          <div class="text-xs text-slate-300">Accurate recognition.</div>
        </div>
      </div>
    </div>
  </section>
  <footer class="mt-auto border-t border-white/10">
    <div class="mx-auto max-w-6xl px-4 py-6 text-center text-sm text-slate-300">
      © A&T Group at Strategy First AI Hackathon 2025
    </div>
  </footer>
  <script>
    const modeSel = document.getElementById('mode');
    const pdfInput = document.getElementById('pdfInput');
    const audioInput = document.getElementById('audioInput');
    const sttLangRow = document.getElementById('sttLangRow');
    const langDiv = document.getElementById('langDiv');
    const progressWrap = document.getElementById('progressWrap');
    const player = document.getElementById('player');
    const outputText = document.getElementById('outputText');
    const pdfFileInput = document.getElementById('pdf');
    const audioFileInput = document.getElementById('audio');
    const pdfName = document.getElementById('pdfName');
    const audioName = document.getElementById('audioName');

    // Disable STT-related options if not available
    const sttDisabled = !%(has_stt)s;
    if (sttDisabled) {
      const sttOptions = `
        <option value="audio_text" disabled>Audio → Text • Speech to text (Disabled)</option>
        <option value="audio_translate" disabled>Audio → Translate • STT and translate (Disabled)</option>
        <option value="audio_audio" disabled>Audio → Audio • Speak back (Disabled)</option>
      `;
      document.getElementById('mode').innerHTML += sttOptions;
      document.querySelectorAll('#sttLangRow, .stt-feature').forEach(el => el.style.display = 'none');
    }

    function updateFormVisibility() {
      const m = modeSel.value;
      const pdfNeeded = (m === 'pdf_audio' || m === 'pdf_translate' || m === 'pdf_translate_audio');
      const audioNeeded = (m === 'audio_text' || m === 'audio_translate' || m === 'audio_audio');
      const sttLangNeeded = (m === 'audio_text' || m === 'audio_translate' || m === 'audio_audio');
      const langNeeded = (m === 'pdf_audio' || m === 'pdf_translate' || m === 'pdf_translate_audio' || m === 'audio_translate' || m === 'audio_audio');

      pdfInput.classList.toggle('hidden', !pdfNeeded);
      audioInput.classList.toggle('hidden', !audioNeeded);
      sttLangRow.classList.toggle('hidden', !sttLangNeeded);
      langDiv.classList.toggle('hidden', !langNeeded);

      // Reset file inputs when switching modes
      if (pdfNeeded) {
        audioFileInput.value = '';
        audioName.textContent = 'No file chosen';
      } else if (audioNeeded) {
        pdfFileInput.value = '';
        pdfName.textContent = 'No file chosen';
      }
    }

    modeSel.addEventListener('change', updateFormVisibility);
    updateFormVisibility(); // Initial call

    pdfFileInput.addEventListener('change', function() {
      pdfName.textContent = this.files.length > 0 ? this.files[0].name : 'No file chosen';
    });

    audioFileInput.addEventListener('change', function() {
      audioName.textContent = this.files.length > 0 ? this.files[0].name : 'No file chosen';
    });

    document.getElementById('toolForm').addEventListener('submit', async function(e) {
      e.preventDefault();
      progressWrap.classList.remove('hidden');
      player.classList.add('hidden');
      outputText.classList.add('hidden');
      outputText.value = '';

      const mode = modeSel.value;
      const formData = new FormData(this);
      let url = '';

      if (mode === 'pdf_audio') {
        url = '/pdf-to-audio';
      } else if (mode === 'pdf_translate') {
        url = '/pdf-to-translate';
      } else if (mode === 'pdf_translate_audio') {
        url = '/pdf-to-translate-audio';
      } else if (mode === 'audio_text') {
        url = '/audio-to-text';
      } else if (mode === 'audio_translate') {
        url = '/audio-to-translate';
      } else if (mode === 'audio_audio') {
        url = '/audio-to-audio';
      }

      try {
        const response = await fetch(url, {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || 'An unknown error occurred.');
        }

        if (mode.includes('audio') && !mode.includes('text')) { // If the result is an audio file
          const blob = await response.blob();
          const audioUrl = URL.createObjectURL(blob);
          player.src = audioUrl;
          player.classList.remove('hidden');
        } else { // If the result is text/json
          const data = await response.json();
          outputText.value = data.translated_text || data.text || JSON.stringify(data, null, 2);
          outputText.classList.remove('hidden');
        }
      } catch (error) {
        console.error('Error:', error);
        outputText.value = 'Error: ' + error.message;
        outputText.classList.remove('hidden');
      } finally {
        progressWrap.classList.add('hidden');
      }
    });
  </script>
</body>
</html>
"""

# ---------- Routes ----------
@app.route('/')
def home():
    stt_disabled_style = 'display: none;' if not HAS_STT else ''
    stt_options = '' if not HAS_STT else '''
        <option value="audio_text">Audio → Text • Speech to text</option>
        <option value="audio_translate">Audio → Translate • STT and translate</option>
        <option value="audio_audio">Audio → Audio • Speak back in target language</option>
    '''
    has_stt_lower = str(HAS_STT).lower()
    
    html = INDEX_HTML.replace('%(stt_disabled)s', stt_disabled_style)
    html = html.replace('%(stt_options)s', stt_options)
    html = html.replace('%(has_stt)s', has_stt_lower) # Corrected placeholder
    
    return html

@app.route('/pdf-to-audio', methods=['POST'])
def pdf_to_audio():
    try:
        pdf = request.files.get('pdf')
        lang = request.form.get('lang', 'en')
        if not pdf:
            return "No PDF uploaded", 400
        text = extract_text_from_pdf(pdf)
        mp3_path = tts_to_tempfile(text, lang)

        @after_this_request
        def cleanup(response):
            try:
                os.remove(mp3_path)
            except Exception as e:
                logging.error(f"Failed to delete temp file {mp3_path}: {e}")
            return response

        return send_file(mp3_path, mimetype='audio/mpeg', as_attachment=True, download_name='audiobook.mp3')
    except Exception as e:
        logging.error(f"Error in pdf_to_audio: {str(e)}")
        return str(e), 400

@app.route('/pdf-to-translate', methods=['POST'])
def pdf_to_translate():
    try:
        pdf = request.files.get('pdf')
        target = request.form.get('lang', 'en')
        if not pdf:
            return "No PDF uploaded", 400
        text = extract_text_from_pdf(pdf)
        translated = translate_batch_text(text, target)
        return jsonify({"translated_text": translated})
    except Exception as e:
        logging.error(f"Error in pdf_to_translate: {str(e)}")
        return str(e), 400

@app.route('/pdf-to-translate-audio', methods=['POST'])
def pdf_to_translate_audio():
    try:
        pdf = request.files.get('pdf')
        target = request.form.get('lang', 'en')
        if not pdf:
            return "No PDF uploaded", 400
        text = extract_text_from_pdf(pdf)
        translated = translate_batch_text(text, target)
        mp3_path = tts_to_tempfile(translated, target)

        @after_this_request
        def cleanup(response):
            try:
                os.remove(mp3_path)
            except Exception as e:
                logging.error(f"Failed to delete temp file {mp3_path}: {e}")
            return response

        return send_file(mp3_path, mimetype='audio/mpeg', as_attachment=True, download_name='translated_audiobook.mp3')
    except Exception as e:
        logging.error(f"Error in pdf_to_translate_audio: {str(e)}")
        return str(e), 400

@app.route('/audio-to-text', methods=['POST'])
def audio_to_text():
    if not HAS_STT:
        return "Speech-to-Text functionality is disabled.", 400
    try:
        audio = request.files.get('audio')
        stt_lang = request.form.get('stt_lang', 'en-US')
        if not audio:
            return "No audio uploaded", 400
        # check_file_size(audio) # Already handled in convert_to_wav
        wav_path = convert_to_wav(audio)
        text = stt_google(wav_path, language=stt_lang)
        os.remove(wav_path)
        return jsonify({"text": text})
    except Exception as e:
        logging.error(f"Error in audio_to_text: {str(e)}")
        return str(e), 400

@app.route('/audio-to-translate', methods=['POST'])
def audio_to_translate():
    if not HAS_STT:
        return "Speech-to-Text functionality is disabled.", 400
    try:
        audio = request.files.get('audio')
        stt_lang = request.form.get('stt_lang', 'en-US')
        target = request.form.get('lang', 'en')
        if not audio:
            return "No audio uploaded", 400
        # check_file_size(audio) # Already handled in convert_to_wav
        wav_path = convert_to_wav(audio)
        text = stt_google(wav_path, language=stt_lang)
        os.remove(wav_path)
        translated = translate_batch_text(text, target)
        return jsonify({"text": text, "translated_text": translated})
    except Exception as e: # Corrected syntax
        logging.error(f"Error in audio_to_translate: {str(e)}")
        return str(e), 400

@app.route('/audio-to-audio', methods=['POST'])
def audio_to_audio():
    if not HAS_STT:
        return "Speech-to-Text functionality is disabled.", 400
    try:
        audio = request.files.get('audio')
        stt_lang = request.form.get('stt_lang', 'en-US')
        target = request.form.get('lang', 'en')
        if not audio:
            return "No audio uploaded", 400
        # check_file_size(audio) # Already handled in convert_to_wav
        wav_path = convert_to_wav(audio)
        text = stt_google(wav_path, language=stt_lang)
        os.remove(wav_path)
        translated = translate_batch_text(text, target)
        mp3_path = tts_to_tempfile(translated, target)

        @after_this_request
        def cleanup(response):
            try:
                os.remove(mp3_path)
            except Exception as e:
                logging.error(f"Failed to delete temp file {mp3_path}: {e}")
            return response

        return send_file(mp3_path, mimetype='audio/mpeg', as_attachment=True, download_name='translated_audio.mp3')
    except Exception as e:
        logging.error(f"Error in audio_to_audio: {str(e)}")
        return str(e), 400

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
