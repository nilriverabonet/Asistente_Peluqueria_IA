import os
import json
import threading
import warnings
import tkinter as tk
from tkinter import scrolledtext, messagebox
from dotenv import load_dotenv

# Ocultamos avisos internos de librerías para mantener limpia la consola
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai

# 1. CARGA DE LA API KEY DESDE EL ARCHIVO .env
# Usamos variables de entorno para no dejar la clave privada escrita en el código
load_dotenv()
API_KEY = os.getenv("API_KEY")

if API_KEY and API_KEY != "tu_clave_api_aqui":
    genai.configure(api_key=API_KEY, transport="rest")


# 2. LECTURA DEL ARCHIVO DE CONTEXTO (servicios.txt)
def cargar_contexto():
    """
    Lee el archivo servicios.txt para pasárselo a la IA como contexto
    (In-Context Learning) sin necesidad de entrenar un modelo desde cero.
    """
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "servicios.txt")
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return archivo.read().strip()
    except FileNotFoundError:
        return ""


# 3. CONSULTA A LA API DE GEMINI Y EXTRACCIÓN DEL JSON
def consultar_gemini(pregunta, contexto):
    """
    Envía el contexto de la peluquería y la pregunta a Gemini, y extrae
    únicamente el texto relevante de la respuesta en formato JSON.
    """
    if not API_KEY or API_KEY == "tu_clave_api_aqui":
        return "⚠️ Error: Configura una API_KEY válida en tu archivo .env."

    if not contexto:
        return "⚠️ Error: No se encontró el archivo servicios.txt."

    # Construimos el prompt delimitando que solo responda como la peluquería
    prompt = f"""Eres el asistente virtual de la 'Peluquería Antigua Grecia'.
Responde a la pregunta del cliente basándote ÚNICAMENTE en esta información:

{contexto}

Reglas:
- Sé amable, breve y claro.
- Si preguntan algo que no tenga relación con la peluquería, responde que solo puedes atender dudas sobre la Peluquería Antigua Grecia.
- Usa texto plano con guiones (-), sin usar asteriscos (**) de Markdown.

Pregunta del cliente: {pregunta}"""

    # Probamos en orden por si algún servidor corta la conexión (10054) o está saturado (503)
    modelos = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.1-flash-lite"]
    ultimo_error = None

    for nombre_modelo in modelos:
        try:
            modelo = genai.GenerativeModel(nombre_modelo)
            respuesta = modelo.generate_content(prompt, request_options={"timeout": 12})

            # Procesamos la respuesta en formato JSON para extraer solo el texto
            datos_json = json.loads(json.dumps(respuesta.to_dict(), ensure_ascii=False))
            texto = datos_json["candidates"][0]["content"]["parts"][0]["text"]

            return texto.replace("**", "").strip()
        except Exception as error:
            ultimo_error = error
            continue

    # Si fallan todos los intentos, avisamos al usuario sin cerrar el programa
    return f"⚠️ Error de conexión con la API de Gemini: {ultimo_error}"


# 4. FUNCIONES DE LA INTERFAZ GRÁFICA (TKINTER)
def mostrar_mensaje(remitente, texto, etiqueta):
    """
    Habilita temporalmente el área de chat para añadir un mensaje nuevo,
    hace scroll hasta el final y vuelve a bloquearla para evitar que se borre.
    """
    area_chat.config(state=tk.NORMAL)
    area_chat.insert(tk.END, f"{remitente}\n", etiqueta)
    area_chat.insert(tk.END, f"{texto}\n\n", "cuerpo")
    area_chat.see(tk.END)
    area_chat.config(state=tk.DISABLED)


def enviar_pregunta(pregunta_rapida=None):
    """
    Recoge la pregunta del cuadro de texto (o de un botón rápido), limpia el
    campo de entrada y consulta a la IA en segundo plano para no congelar la ventana.
    """
    if str(boton_enviar["state"]) == tk.DISABLED:
        return

    pregunta = pregunta_rapida if pregunta_rapida else entrada_usuario.get().strip()
    if not pregunta:
        messagebox.showwarning("Aviso", "Por favor, escribe una pregunta antes de enviar.")
        return

    # Limpiamos el cuadro de texto tras enviar y mostramos la pregunta del usuario
    if not pregunta_rapida:
        entrada_usuario.delete(0, tk.END)

    mostrar_mensaje("👤 Tú:", pregunta, "usuario")
    boton_enviar.config(state=tk.DISABLED, text="Pensando...")

    # Usamos un hilo secundario para que la ventana no se quede "No responde"
    def tarea_ia():
        respuesta = consultar_gemini(pregunta, CONTEXTO_PELUQUERIA)
        ventana.after(0, lambda: finalizar_respuesta(respuesta))

    threading.Thread(target=tarea_ia, daemon=True).start()


def finalizar_respuesta(respuesta):
    """Muestra la respuesta de la IA en el chat y reactiva el botón de enviar."""
    mostrar_mensaje("💬 Asistente Antigua Grecia:", respuesta, "asistente")
    boton_enviar.config(state=tk.NORMAL, text="Enviar ➤")
    entrada_usuario.focus()


def limpiar_chat():
    """Borra el historial del chat y vuelve a mostrar el saludo inicial."""
    area_chat.config(state=tk.NORMAL)
    area_chat.delete("1.0", tk.END)
    area_chat.config(state=tk.DISABLED)
    mostrar_mensaje(
        "🏺 Peluquería Antigua Grecia ✨",
        "¡Bienvenido/a! Escribe tu pregunta abajo o usa los botones rápidos para "
        "consultar nuestros servicios, precios y horarios.",
        "bienvenida",
    )


# ==============================================================================
# 5. CREACIÓN DE LA VENTANA PRINCIPAL
# ==============================================================================
CONTEXTO_PELUQUERIA = cargar_contexto()

ventana = tk.Tk()
ventana.title("Peluquería Antigua Grecia — Asistente IA")
ventana.geometry("680x560")
ventana.minsize(520, 420)
ventana.configure(bg="#f1f5f9")

# Cabecera superior
cabecera = tk.Frame(ventana, bg="#1e1b4b", padx=16, pady=12)
cabecera.pack(fill=tk.X)

tk.Label(
    cabecera,
    text="🏺 Peluquería Antigua Grecia ✨",
    font=("Segoe UI", 13, "bold"),
    bg="#1e1b4b",
    fg="white",
).pack(anchor="w")

tk.Label(
    cabecera,
    text="Asistente Virtual con IA (Google Gemini) • Sin cita previa",
    font=("Segoe UI", 9),
    bg="#1e1b4b",
    fg="#c7d2fe",
).pack(anchor="w")

# Barra de botones de preguntas rápidas
barra_rapida = tk.Frame(ventana, bg="#f1f5f9", padx=14, pady=8)
barra_rapida.pack(fill=tk.X)

preguntas_rapidas = [
    ("💇 Cortes y Peinados", "¿Cuánto cuestan el corte y el peinado?"),
    ("🎨 Tintes", "¿Qué opciones de tinte tenéis y qué precios tienen?"),
    ("🕒 Horario", "¿Cuál es el horario de la peluquería?"),
    ("🧔 Barbería", "¿Cuánto cuesta el servicio de barbería?"),
]

for texto_btn, consulta_btn in preguntas_rapidas:
    tk.Button(
        barra_rapida,
        text=texto_btn,
        font=("Segoe UI", 9),
        bg="#e2e8f0",
        fg="#1e293b",
        relief=tk.FLAT,
        padx=8,
        pady=3,
        cursor="hand2",
        command=lambda q=consulta_btn: enviar_pregunta(q),
    ).pack(side=tk.LEFT, padx=3)

tk.Button(
    barra_rapida,
    text="🗑️ Limpiar",
    font=("Segoe UI", 9),
    bg="#e2e8f0",
    fg="#475569",
    relief=tk.FLAT,
    padx=8,
    pady=3,
    cursor="hand2",
    command=limpiar_chat,
).pack(side=tk.RIGHT)

# Área central del chat con Scrollbar integrada
area_chat = scrolledtext.ScrolledText(
    ventana,
    wrap=tk.WORD,
    font=("Segoe UI", 10),
    bg="white",
    fg="#1e293b",
    padx=14,
    pady=12,
    relief=tk.SOLID,
    bd=1,
)
area_chat.pack(padx=14, pady=(0, 8), fill=tk.BOTH, expand=True)

# Colores y estilos para diferenciar los mensajes en el chat
area_chat.tag_config("bienvenida", foreground="#1e1b4b", font=("Segoe UI", 10, "bold"))
area_chat.tag_config("usuario", foreground="#1d4ed8", font=("Segoe UI", 10, "bold"))
area_chat.tag_config("asistente", foreground="#047857", font=("Segoe UI", 10, "bold"))
area_chat.tag_config("cuerpo", foreground="#1e293b", font=("Segoe UI", 10))

limpiar_chat()

# Panel inferior con cuadro de entrada y botón Enviar
panel_inferior = tk.Frame(ventana, bg="#f1f5f9", padx=14, pady=10)
panel_inferior.pack(fill=tk.X)

entrada_usuario = tk.Entry(panel_inferior, font=("Segoe UI", 10), relief=tk.SOLID, bd=1)
entrada_usuario.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
entrada_usuario.focus()

boton_enviar = tk.Button(
    panel_inferior,
    text="Enviar ➤",
    font=("Segoe UI", 10, "bold"),
    bg="#2563eb",
    fg="white",
    relief=tk.FLAT,
    padx=16,
    pady=5,
    cursor="hand2",
    command=enviar_pregunta,
)
boton_enviar.pack(side=tk.RIGHT)

# Permitimos enviar también pulsando la tecla Enter
entrada_usuario.bind("<Return>", lambda e: enviar_pregunta())

if __name__ == "__main__":
    ventana.mainloop()
