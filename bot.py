import streamlit as st
import os
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Cargar variables de entorno
load_dotenv()

st.set_page_config(page_title="Bot Asistente", page_icon="🤖")

# Estilos personalizados
st.markdown("""
    <style>
        .stApp { background-color: white; color: black; }
        section[data-testid="stSidebar"] { background-color: #F3F1EB; opacity: 0.7; }
        .stMarkdown p, .stText, .stHeader, .stSubheader { color: black !important; }
        div.stButton > button {
            background-color: white; color: black; border: 1px solid gray;
        }
        div.stButton > button:hover { background-color: #f0f0f0; color: black; }
        .stChatMessage.user, .stChatMessage.bot {
            background-color: white; color: black;
            border-radius: 10px; padding: 10px;
        }
        section[data-testid="stChatInput"] { background-color: white; }
        textarea::placeholder, input::placeholder { color: gray !important; opacity: 0.7; }
        header[data-testid="stHeader"], footer { background-color: white; }
    </style>
""", unsafe_allow_html=True)

# Título
st.markdown("<h1 style='text-align: center;'>🤖 Asistente ni tan inteligente</h1>", unsafe_allow_html=True)

# Prompt del sistema (opcional)
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")

# Mensajes en sesión
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "user", "content": SYSTEM_PROMPT}]

# API Key de Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("❌ Falta la clave de API de Gemini. Configura GEMINI_API_KEY en tu archivo .env.")
    st.stop()

# Configuración Google Sheets
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not GOOGLE_CREDENTIALS_JSON:
    st.error("❌ Credenciales de Google no encontradas en el entorno.")
    st.stop()

try:
    credentials_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    gc = gspread.authorize(creds)
    sh = gc.open("MensajesBot")
    worksheet = sh.sheet1
except Exception as e:
    st.error(f"❌ Error al conectar con Google Sheets: {e}")
    st.stop()



# Función para extraer JSON del texto
def extraer_json(texto):
    try:
        json_str = re.search(r'\{.*\}', texto, re.DOTALL).group()
        return json.loads(json_str)
    except Exception:
        return None

# Guardar en Google Sheets
def guardar_en_google_sheets(nombre, email, comentario, mensaje_original):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fila = [timestamp, nombre, email, comentario, mensaje_original]
    worksheet.append_row(fila)

# Llamar a Gemini
def get_ai_response(user_input):
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 🔁 Convertir todo el historial al formato de Gemini
    contents = []
    for msg in st.session_state.messages:
        role = (
            "user" if msg["role"] == "user"
            else "model" if msg["role"] == "assistant"
            else None
        )
        if role:
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

    try:
        response = requests.post(
            url="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": GEMINI_API_KEY
            },
            json={"contents": contents}  # ← usa historial completo
        )

        data = response.json()
        ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        return ai_response

    except Exception as e:
        return f"⚠️ Error al generar respuesta: {str(e)}"

# Sidebar
with st.sidebar:
    st.subheader("Info")
    st.info("Modelo: Gemini 2.0 Flash")
    if st.button("🧹 Limpiar historial de conversación"):
        st.session_state.messages = [{"role": "user", "content": SYSTEM_PROMPT}]
        st.success("Historial limpiado ✅")
        st.rerun()

# Mostrar historial de mensajes
for msg in st.session_state.messages[1:]:
    role_class = "user" if msg["role"] == "user" else "assistant"
    avatar = "🧑" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(f"<div class='stChatMessage {role_class}'>{msg['content']}</div>", unsafe_allow_html=True)

# Entrada del usuario
if prompt := st.chat_input("✍️ Escribí tu mensaje..."):
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Pensando..."):
            respuesta = get_ai_response(prompt)

            # Si contiene JSON válido, guardar
            datos = extraer_json(respuesta)
            if datos and all(k in datos for k in ["nombre", "email", "comentario"]):
                guardar_en_google_sheets(datos["nombre"], datos["email"], datos["comentario"], prompt)
                st.markdown(
                    "<div style='background-color:#d4edda;padding:10px;border-radius:8px;color:#155724;'>✅ ¡Datos enviados correctamente!</div>",
                    unsafe_allow_html=True
                )

            st.markdown(f"<div class='stChatMessage assistant'>{respuesta}</div>", unsafe_allow_html=True)
