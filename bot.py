import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import re
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Cargar variables de entorno
load_dotenv()

st.set_page_config(page_title="Bot Asistente", page_icon="🤖")

st.markdown("""
    <style>
        /* 🎯 Fondo del contenedor principal (toda la app) */
        .stApp {
            background-color: white;  /* ← Color de fondo principal */
            color: black;  /* ← Color del texto por defecto */
        }

        /* 🎯 Sidebar (barra lateral izquierda) */
        section[data-testid="stSidebar"] {
            background-color: #F3F1EB;  /* ← Fondo del sidebar */
            opacity: 0.7;
        }

        /* 🎯 Texto general en markdown, encabezados y subencabezados */
        .stMarkdown p, .stText, .stHeader, .stSubheader {
            color: black !important;  /* ← Color del texto principal */
        }

        /* 🎯 Botones como "Limpiar historial" */
        div.stButton > button {
            background-color: white;  /* ← Fondo del botón */
            color: black;  /* ← Texto del botón */
            border: 1px solid gray;  /* ← Borde del botón */
        }

        div.stButton > button:hover {
            background-color: #f0f0f0;  /* ← Hover sobre el botón */
            color: black;
        }

        /* 🎯 Mensajes del usuario */
        .stChatMessage.user {
            background-color: white;  /* ← Fondo de los mensajes del usuario */
            color: black;
            border-radius: 10px;
            padding: 10px;
        }

        /* 🎯 Mensajes del bot */
        .stChatMessage.bot {
            background-color: white;  /* ← Fondo de los mensajes del bot */
            color: black;
            border-radius: 10px;
            padding: 10px;
        }

        /* 🎯 Input de texto del chat (contenedor inferior) */
        section[data-testid="stChatInput"] {
            background-color: white;  /* ← Fondo del contenedor del input */
        }

        

        /* 🎯 Placeholder del input (texto guía) */
        textarea::placeholder, input::placeholder {
            color: gray !important;
            opacity: 0.7;
        }

        /* 🎯 Header horizontal superior (logo y título) */
        header[data-testid="stHeader"] {
            background-color: white;  /* ← Fondo del header */
        }

        /* 🎯 Pie de página (footer) */
        footer {
            background-color: white;  /* ← Fondo del footer */
        }
    </style>
""", unsafe_allow_html=True)


# Título personalizado
st.markdown("<h1 style='text-align: center;'>🤖 Asistente ni tan inteligente</h1>", unsafe_allow_html=True)

# Obtener API Key OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    st.error("❌ API key no encontrada. Configura tu archivo .env con OPENROUTER_API_KEY")
    st.stop()

# Inicializar cliente OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Configuración Google Sheets
GOOGLE_SHEET_NAME = "NombreDeTuGoogleSheet"  # Cambia esto al nombre de tu Google Sheet
GOOGLE_CREDENTIALS_FILE = "credentials.json"  # Archivo JSON con credenciales de servicio

# Autenticación y conexión con Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
    gc = gspread.authorize(creds)
    sh = gc.open("MensajesBot")
    worksheet = sh.sheet1
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# Función para extraer JSON del texto
def extraer_json(texto):
    try:
        json_str = re.search(r'\{.*\}', texto, re.DOTALL).group()
        return json.loads(json_str)
    except Exception:
        return None

# Función para guardar datos en Google Sheets con timestamp
def guardar_en_google_sheets(nombre, email, comentario, mensaje_original):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fila = [timestamp, nombre, email, comentario, mensaje_original]
    worksheet.append_row(fila)

# Función para obtener respuesta IA
def get_ai_response(user_input):
    st.session_state.messages.append({"role": "user", "content": user_input})
    try:
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            messages=st.session_state.messages,
            temperature=0.6,
            extra_headers={
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "Asistente IA"
            }
        )
        ai_response = completion.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        return ai_response
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# Sidebar
with st.sidebar:
    st.subheader("Info")
    st.info("Modelo: GLM-4.5-AIR")
    if st.button("🧹 Limpiar historial de conversación"):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.success("Historial limpiado ✅")
        st.rerun()

# Mostrar historial de mensajes con estilo
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

            # Intentar extraer JSON y guardar en Google Sheets si es válido
            datos = extraer_json(respuesta)
            if datos and all(k in datos for k in ["nombre", "email", "comentario"]):
                guardar_en_google_sheets(datos["nombre"], datos["email"], datos["comentario"], prompt)
                st.markdown(
                    "<div style='background-color:#d4edda;padding:10px;border-radius:8px;color:#155724;'>✅ ¡Datos enviados correctamente!</div>",
                    unsafe_allow_html=True
                )

            st.markdown(f"<div class='stChatMessage assistant'>{respuesta}</div>", unsafe_allow_html=True)
