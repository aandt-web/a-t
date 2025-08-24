import logging
import subprocess
import time
from flask import Flask, request, send_file, jsonify, after_this_request
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
import os
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# HTML content (using your provided INDEX_HTML)
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Lingua Flow – Transform Documents & Audio with AI</title>
  <!-- Tailwind (CDN for quick drop-in) -->
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
            glass: '0 10px 30px rgba(0,0,0,.35)'
          },
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
    @keyframes gradientShift {
      0% { background-position: 0% 50% }
      50% { background-position: 100% 50% }
      100% { background-position: 0% 50% }
    }
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
          <li class="flex items-start gap-3">
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
                <option value="audio_text">Audio → Text • Speech to text</option>
                <option value="audio_translate">Audio → Translate • STT and translate</option>
                <option value="audio_audio">Audio → Audio • Speak back in target language</option>
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
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg>
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
      <div class="glass rounded-xl p-4 flex items-start gap-3">
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

    function updateFormVisibility() {
      const m = modeSel.value;
      const pdfNeeded = (m === 'pdf_audio' || m === 'pdf_translate' || m === 'pdf_translate_audio');
      pdfInput.classList.toggle('hidden', !pdfNeeded);
      audioInput.classList.toggle('hidden', pdfNeeded);
      sttLangRow.classList.toggle('hidden', !(m === 'audio_text' || m === 'audio_translate' || m === 'audio_audio'));
      langDiv.classList.toggle('hidden', m === 'pdf_audio' || m === 'audio_text');
    }

    function updateFileStatus() {
      const p = pdfFileInput?.files?.[0];
      const a = audioFileInput?.files?.[0];
      if (p) pdfName.textContent = p.name; else pdfName.textContent = 'No file chosen';
      if (a) audioName.textContent = a.name; else audioName.textContent = 'No file chosen';
    }

    modeSel.addEventListener('change', updateFormVisibility);
    pdfFileInput.addEventListener('change', updateFileStatus);
    audioFileInput.addEventListener('change', updateFileStatus);
    updateFormVisibility();

    document.getElementById('toolForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      progressWrap.classList.remove('hidden');
      player.classList.add('hidden');
      outputText.classList.add('hidden');
      outputText.value = '';

      const m = modeSel.value;
      const lang = document.getElementById('lang').value;
      const sttLang = document.getElementById('stt_lang').value;
      const maxFileSize = 10 * 1024 * 1024; // 10MB

      const fd = new FormData();
      if (m.startsWith('pdf')) {
        const pdf = pdfFileInput.files[0];
        if (!pdf) { alert('Please choose a PDF.'); progressWrap.classList.add('hidden'); return; }
        if (pdf.size > maxFileSize) { alert('Document is too large (max 10MB).'); progressWrap.classList.add('hidden'); return; }
        fd.append('pdf', pdf);
        if (m !== 'pdf_audio') fd.append('lang', lang);
      } else {
        const audio = audioFileInput.files[0];
        if (!audio) { alert('Please choose an audio file.'); progressWrap.classList.add('hidden'); return; }
        if (audio.size > maxFileSize) { alert('Audio is too large (max 10MB).'); progressWrap.classList.add('hidden'); return; }
        fd.append('audio', audio);
        if (m !== 'audio_text') fd.append('lang', lang);
        fd.append('stt_lang', sttLang);
      }

      const endpoints = {
        pdf_audio: '/pdf-to-audio',
        pdf_translate: '/pdf-to-translate',
        pdf_translate_audio: '/pdf-to-translate-audio',
        audio_text: '/audio-to-text',
        audio_translate: '/audio-to-translate',
        audio_audio: '/audio-to-audio'
      };

      try {
        const res = await fetch(endpoints[m], { method: 'POST', body: fd });
        if (!res.ok) {
          const msg = await res.text();
          alert(`Error: ${msg}`);
          progressWrap.classList.add('hidden');
          return;
        }

        if (m === 'pdf_audio' || m === 'pdf_translate_audio' || m === 'audio_audio') {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          player.src = url;
          player.classList.remove('hidden');
        } else {
          const data = await res.json();
          const text = data.translated_text || data.text || JSON.stringify(data);
          outputText.value = text;
          outputText.classList.remove('hidden');
        }
      } catch (e) {
        alert(`Network error: ${e.message}`);
      }

      progressWrap.classList.add('hidden');
    });
  </script>
</body>
</html>
"""

# ---------- PDF Handling ----------
def extract_text_from_pdf(pdf_file):
    try:
        pdf = PdfReader(pdf_file)
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        return text
    except PdfReadError as e:
        logging.error(f"PDF Read Error: {e}")
        return None

# ---------- Translation ----------
def translate_text(text, target_lang="en"):
    try:
        response = requests.post(
            "http://192.168.100.211:5000/translate",
            json={"q": text, "source": "en", "target": target_lang},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json().get("translatedText")
    except requests.RequestException as e:
        logging.error(f"Translation Error: {e}")
        return None

# ---------- Speech to Text ----------
def speech_to_text(audio_file, lang="en-US"):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language=lang)
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        logging.error(f"STT Error: {e}")
        return None

# ---------- Text to Speech ----------
def text_to_speech(text, lang="en"):
    try:
        tts = gTTS(text=text, lang=lang)
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp_file.name)
        return tmp_file.name
    except Exception as e:
        logging.error(f"TTS Error: {e}")
        return None

# ---------- Routes ----------
@app.route("/")
def home():
    return INDEX_HTML

# --- PDF → Audio ---
@app.route("/pdf-to-audio", methods=["POST"])
def pdf_to_audio():
    file = request.files.get("pdf")
    if not file:
        return jsonify({"error": "No PDF uploaded"}), 400

    text = extract_text_from_pdf(file)
    if not text:
        return jsonify({"error": "PDF extraction failed"}), 500

    audio_path = text_to_speech(text)
    if not audio_path:
        return jsonify({"error": "TTS failed"}), 500

    @after_this_request
    def cleanup(response):
        try:
            os.remove(audio_path)
        except Exception as e:
            logging.error(f"Cleanup error: {e}")
        return response

    return send_file(audio_path, as_attachment=True, download_name="audio.mp3")

# --- PDF → Translate ---
@app.route("/pdf-to-translate", methods=["POST"])
def pdf_to_translate():
    file = request.files.get("pdf")
    target_lang = request.form.get("lang", "en")

    if not file:
        return jsonify({"error": "No PDF uploaded"}), 400

    text = extract_text_from_pdf(file)
    if not text:
        return jsonify({"error": "PDF extraction failed"}), 500

    translated = translate_text(text, target_lang)
    if not translated:
        return jsonify({"error": "Translation failed"}), 500

    return jsonify({"translated_text": translated})

# --- PDF → Translate → Audio ---
@app.route("/pdf-to-translate-audio", methods=["POST"])
def pdf_to_translate_audio():
    file = request.files.get("pdf")
    target_lang = request.form.get("lang", "en")

    if not file:
        return jsonify({"error": "No PDF uploaded"}), 400

    text = extract_text_from_pdf(file)
    if not text:
        return jsonify({"error": "PDF extraction failed"}), 500

    translated = translate_text(text, target_lang)
    if not translated:
        return jsonify({"error": "Translation failed"}), 500

    audio_path = text_to_speech(translated, lang=target_lang)
    if not audio_path:
        return jsonify({"error": "TTS failed"}), 500

    @after_this_request
    def cleanup(response):
        try:
            os.remove(audio_path)
        except Exception as e:
            logging.error(f"Cleanup error: {e}")
        return response

    return send_file(audio_path, as_attachment=True, download_name="translated_audio.mp3")

# --- Audio → Text ---
@app.route("/audio-to-text", methods=["POST"])
def audio_to_text():
    file = request.files.get("audio")
    stt_lang = request.form.get("stt_lang", "en-US")

    if not file:
        return jsonify({"error": "No audio uploaded"}), 400

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    file.save(tmp_file.name)

    text = speech_to_text(tmp_file.name, stt_lang)
    os.remove(tmp_file.name)

    if not text:
        return jsonify({"error": "STT failed"}), 500

    return jsonify({"text": text})

# --- Audio → Translate ---
@app.route("/audio-to-translate", methods=["POST"])
def audio_to_translate():
    file = request.files.get("audio")
    target_lang = request.form.get("lang", "en")

    if not file:
        return jsonify({"error": "No audio uploaded"}), 400

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    file.save(tmp_file.name)

    text = speech_to_text(tmp_file.name)
    os.remove(tmp_file.name)

    if not text:
        return jsonify({"error": "STT failed"}), 500

    translated = translate_text(text, target_lang)
    if not translated:
        return jsonify({"error": "Translation failed"}), 500

    return jsonify({"translated_text": translated})

# --- Audio → Audio ---
@app.route("/audio-to-audio", methods=["POST"])
def audio_to_audio():
    file = request.files.get("audio")
    target_lang = request.form.get("lang", "en")
    stt_lang = request.form.get("stt_lang", "en-US")

    if not file:
        return jsonify({"error": "No audio uploaded"}), 400

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    file.save(tmp_file.name)

    text = speech_to_text(tmp_file.name, stt_lang)
    os.remove(tmp_file.name)

    if not text:
        return jsonify({"error": "STT failed"}), 500

    translated = translate_text(text, target_lang)
    if not translated:
        return jsonify({"error": "Translation failed"}), 500

    audio_path = text_to_speech(translated, lang=target_lang)
    if not audio_path:
        return jsonify({"error": "TTS failed"}), 500

    @after_this_request
    def cleanup(response):
        try:
            os.remove(audio_path)
        except Exception as e:
            logging.error(f"Cleanup error: {e}")
        return response

    return send_file(audio_path, as_attachment=True, download_name="translated_audio.mp3")

# ---------- Run ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
