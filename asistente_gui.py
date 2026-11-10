import os
import json
import threading
import warnings
import tkinter as tk
from tkinter import scrolledtext, messagebox
from dotenv import load_dotenv

# Silenciamos avisos de versiones futuras de librerías internas para mantener limpia la consola
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai

# ==============================================================================
# 1. CARGA SEGURA DE VARIABLES DE ENTORNO (.env)
# ==============================================================================
# Usamos load_dotenv() para cargar en memoria las variables definidas en el
# archivo .env local. De esta forma, la API Key nunca queda escrita en el código
# fuente (evitando filtraciones de seguridad al subir el proyecto a GitHub).
load_dotenv()
API_KEY = os.getenv("API_KEY")

# Configuramos la librería de Google Gemini con la clave obtenida del entorno.
# Usamos transport="rest" para comunicarnos mediante peticiones HTTP/JSON directas
# evitando bloqueos de red en Windows.
if API_KEY and API_KEY != "tu_clave_api_aqui":
    genai.configure(api_key=API_KEY, transport="rest")


# ==============================================================================
# 2. LECTURA DEL CONTEXTO DE LA PELUQUERÍA (IN-CONTEXT LEARNING)
# ==============================================================================
def cargar_contexto_servicios(ruta_archivo="servicios.txt"):
    """
    Lee el archivo de texto con los servicios, precios y horarios de la peluquería.
    En lugar de entrenar un modelo desde cero (proceso costoso y lento), usamos
    esta información como contexto (In-Context Learning) dentro del prompt.
    """
    # Calculamos la ruta absoluta respecto a este script para evitar errores
    # si el programa se ejecuta desde otra carpeta en la terminal.
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_completa = os.path.join(directorio_actual, ruta_archivo)

    try:
        with open(ruta_completa, "r", encoding="utf-8") as archivo:
            return archivo.read().strip()
    except FileNotFoundError:
        return None
    except Exception as error:
        print(f"Error al leer el archivo de servicios: {error}")
        return None


# ==============================================================================
# 3. COMUNICACIÓN CON LA API DE GEMINI Y MANEJO DE LA RESPUESTA JSON
# ==============================================================================
def consultar_asistente(pregunta_usuario, contexto_peluqueria):
    """
    Construye un prompt delimitado con el contexto de la peluquería, envía la
    consulta a la API de Gemini y procesa el objeto JSON devuelto para extraer
    únicamente el texto limpio de la respuesta.
    """
    # Verificamos que la clave API esté configurada antes de hacer la llamada de red
    if not API_KEY or API_KEY == "tu_clave_api_aqui":
        return (
            "⚠️ Error de configuración: No se ha encontrado una API_KEY válida en el "
            "archivo .env. Por favor, añade tu clave de Google Gemini en el archivo .env."
        )

    if not contexto_peluqueria:
        return (
            "⚠️ Error: No se pudo cargar la información de 'servicios.txt'. "
            "Verifica que el archivo exista en la carpeta del proyecto."
        )

    # Construimos un prompt robusto (Prompt Engineering):
    # - Definimos el rol estricto del asistente (solo responde sobre la peluquería).
    # - Inyectamos los datos reales de servicios.txt para evitar alucinaciones.
    # - Pedimos texto plano sin formato Markdown para que se lea limpio en Tkinter.
    prompt = f"""Eres el asistente virtual oficial de la 'Peluquería Brillo Estelar'.
Tu única función es responder las dudas de los clientes utilizando EXCLUSIVAMENTE la siguiente información oficial de la peluquería:

--- INICIO DEL CONTEXTO DE LA PELUQUERÍA ---
{contexto_peluqueria}
--- FIN DEL CONTEXTO DE LA PELUQUERÍA ---

Reglas estrictas de comportamiento:
1. Responde de forma amable, clara, breve y directa en español.
2. Basa tus respuestas únicamente en los servicios, precios y horarios indicados en el contexto anterior. No inventes servicios ni precios.
3. Si el usuario pregunta por algo que NO tiene relación con la peluquería o sus servicios (por ejemplo, historia, matemáticas, programación u otros temas generales), indícale educadamente que solo puedes responder consultas relacionadas con la Peluquería Brillo Estelar.
4. Escribe la respuesta en texto plano (usa guiones '-' o viñetas '•' para listas, pero NO uses asteriscos '**' de Markdown) para que se visualice limpia en la ventana de chat.

Pregunta del cliente: {pregunta_usuario}
Respuesta del asistente:"""

    # Configuramos la conexión REST con la API Key
    genai.configure(api_key=API_KEY, transport="rest")

    # Lista de modelos Flash rápidos (si uno tiene alta demanda puntual 503, usa el siguiente)
    modelos_disponibles = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
    ]

    ultimo_error = None
    for nombre_modelo in modelos_disponibles:
        try:
            # Instanciamos el modelo preentrenado de Google Gemini
            modelo = genai.GenerativeModel(nombre_modelo)

            # Enviamos el prompt a la API de Gemini con un tiempo máximo de espera (timeout)
            # para evitar que la petición se quede colgada si el servidor tarda en responder
            respuesta_api = modelo.generate_content(
                prompt, request_options={"timeout": 12}
            )

            # ------------------------------------------------------------------
            # MANEJO EXPLÍCITO DE LA RESPUESTA EN FORMATO JSON
            # ------------------------------------------------------------------
            # La API de Gemini estructura su respuesta internamente como un objeto JSON.
            # Convertimos la respuesta a cadena JSON y la procesamos con json.loads()
            # para extraer solo el campo relevante:
            # candidates -> [0] -> content -> parts -> [0] -> text
            respuesta_serializada = json.dumps(
                respuesta_api.to_dict(), ensure_ascii=False
            )
            datos_json = json.loads(respuesta_serializada)

            texto_extraido = (
                datos_json["candidates"][0]["content"]["parts"][0]["text"]
            )

            # Limpiamos posibles caracteres de formato Markdown residuales (como '**')
            # para garantizar que la salida en Tkinter sea 100% limpia y legible.
            texto_limpio = texto_extraido.replace("**", "").strip()
            return texto_limpio

        except KeyError:
            return "⚠️ No se pudo extraer el texto de la respuesta JSON devuelta por la API."
        except Exception as error:
            ultimo_error = error
            continue

    # Si todos los intentos fallan (ej: sin internet o clave inválida), avisamos sin cerrar la app
    return (
        "⚠️ Error al conectar con la API de Gemini. Comprueba tu conexión a internet "
        f"y que tu API_KEY sea válida.\nDetalle técnico: {ultimo_error}"
    )


# ==============================================================================
# 4. FUNCIONES DE LA INTERFAZ GRÁFICA (TKINTER)
# ==============================================================================
def mostrar_mensaje_en_chat(area_chat, remitente, mensaje, etiqueta_color):
    """
    Inserta un nuevo mensaje en el área de texto de Tkinter.
    El widget se mantiene en estado 'disabled' (solo lectura) para impedir que el
    usuario borre el historial a mano, y solo se habilita temporalmente al escribir.
    """
    area_chat.config(state=tk.NORMAL)
    area_chat.insert(tk.END, f"{remitente}", etiqueta_color)
    area_chat.insert(tk.END, f"{mensaje}\n\n", "texto_normal")
    # Desplazamos automáticamente el scroll hasta el final para ver el último mensaje
    area_chat.see(tk.END)
    area_chat.config(state=tk.DISABLED)


def enviar_consulta(entrada_usuario, area_chat, boton_enviar, ventana, contexto_peluqueria):
    """
    Recoge la pregunta escrita por el usuario, limpia el campo de entrada y lanza
    la consulta a la IA en un hilo secundario (threading) para que la ventana de
    Tkinter nunca se congele ("No responde") mientras espera la respuesta de la red.
    """
    # Si el botón ya está deshabilitado esperando respuesta, ignoramos pulsaciones extra
    if str(boton_enviar["state"]) == tk.DISABLED:
        return

    pregunta = entrada_usuario.get().strip()

    # Evitamos hacer llamadas innecesarias a la API si el cuadro de texto está vacío
    if not pregunta:
        messagebox.showwarning(
            "Campo vacío", "Por favor, escribe una pregunta antes de pulsar 'Enviar'."
        )
        return

    # 1. Limpiamos el campo de entrada inmediatamente tras pulsar Enviar
    entrada_usuario.delete(0, tk.END)

    # 2. Mostramos la pregunta del usuario en el área del chat
    mostrar_mensaje_en_chat(area_chat, "👤 Tú: ", pregunta, "usuario")

    # 3. Deshabilitamos temporalmente el botón mientras la IA procesa la respuesta
    boton_enviar.config(state=tk.DISABLED, text="Pensando...")

    # 4. Función interna que se ejecuta en segundo plano para no congelar la interfaz
    def tarea_en_segundo_plano():
        respuesta_ia = consultar_asistente(pregunta, contexto_peluqueria)

        # Devolvemos la actualización visual al hilo principal de Tkinter con ventana.after()
        def actualizar_interfaz():
            mostrar_mensaje_en_chat(
                area_chat, "💬 Asistente: ", respuesta_ia, "asistente"
            )
            boton_enviar.config(state=tk.NORMAL, text="Enviar")
            entrada_usuario.focus()

        ventana.after(0, actualizar_interfaz)

    # Lanzamos el hilo secundario (daemon=True para que se cierre si se cierra la ventana)
    hilo = threading.Thread(target=tarea_en_segundo_plano, daemon=True)
    hilo.start()


def iniciar_interfaz():
    """
    Configura y lanza la ventana principal de la aplicación con Tkinter.
    """
    # Cargamos el contexto de servicios.txt al iniciar la aplicación
    contexto_peluqueria = cargar_contexto_servicios()

    # Creación de la ventana principal
    ventana = tk.Tk()
    ventana.title("Asistente de Peluquería")
    ventana.geometry("620x520")
    ventana.minsize(480, 380)
    ventana.configure(bg="#f0f0f0")

    # --------------------------------------------------------------------------
    # ÁREA DE SALIDA (HISTORIAL DEL CHAT CON SCROLL)
    # --------------------------------------------------------------------------
    # Usamos ScrolledText para que el usuario pueda hacer scroll si la conversación es larga
    area_chat = scrolledtext.ScrolledText(
        ventana,
        wrap=tk.WORD,
        font=("Segoe UI", 10),
        bg="#ffffff",
        fg="#212529",
        padx=12,
        pady=12,
        relief=tk.SOLID,
        bd=1,
    )
    area_chat.pack(padx=12, pady=(12, 8), fill=tk.BOTH, expand=True)

    # Configuramos etiquetas de estilo (colores y negrita) siguiendo el diseño del ejemplo
    area_chat.tag_config("bienvenida", foreground="#333333", font=("Segoe UI", 10))
    area_chat.tag_config("usuario", foreground="#0056b3", font=("Segoe UI", 10, "bold"))
    area_chat.tag_config("asistente", foreground="#1e7e34", font=("Segoe UI", 10, "bold"))
    area_chat.tag_config("texto_normal", foreground="#212529", font=("Segoe UI", 10))

    # Mensaje inicial de bienvenida
    area_chat.insert(
        tk.END,
        "💈 Bienvenido al Asistente de Peluquería.\n"
        "Escribe tu pregunta abajo y presiona 'Enviar'.\n\n",
        "bienvenida",
    )
    area_chat.config(state=tk.DISABLED)

    # --------------------------------------------------------------------------
    # PANEL INFERIOR (CUADRO DE TEXTO DE ENTRADA Y BOTÓN ENVIAR)
    # --------------------------------------------------------------------------
    frame_inferior = tk.Frame(ventana, bg="#f0f0f0")
    frame_inferior.pack(padx=12, pady=(0, 12), fill=tk.X)

    # Cuadro de texto donde el usuario escribe su consulta
    entrada_usuario = tk.Entry(
        frame_inferior,
        font=("Segoe UI", 10),
        relief=tk.SOLID,
        bd=1,
    )
    entrada_usuario.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
    entrada_usuario.focus()

    # Botón 'Enviar' para realizar la consulta
    boton_enviar = tk.Button(
        frame_inferior,
        text="Enviar",
        font=("Segoe UI", 10, "bold"),
        bg="#0066cc",
        fg="#ffffff",
        activebackground="#0052a3",
        activeforeground="#ffffff",
        relief=tk.FLAT,
        padx=16,
        pady=4,
        cursor="hand2",
        command=lambda: enviar_consulta(
            entrada_usuario, area_chat, boton_enviar, ventana, contexto_peluqueria
        ),
    )
    boton_enviar.pack(side=tk.RIGHT)

    # Permitimos enviar la pregunta también pulsando la tecla Enter (<Return>)
    entrada_usuario.bind(
        "<Return>",
        lambda evento: enviar_consulta(
            entrada_usuario, area_chat, boton_enviar, ventana, contexto_peluqueria
        ),
    )

    # Bucle principal de eventos de la ventana
    ventana.mainloop()


if __name__ == "__main__":
    iniciar_interfaz()
