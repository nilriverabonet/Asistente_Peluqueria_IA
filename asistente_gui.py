import os
import json
import threading
import warnings
import tkinter as tk
from tkinter import ttk, messagebox
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
# 2. PALETA DE COLORES Y CONSTANTES VISUALES (DISEÑO MODERNO TKINTER)
# ==============================================================================
COLOR_FONDO_APP = "#f1f5f9"         # Gris azulado muy suave para el fondo general
COLOR_CABECERA = "#1e1b4b"          # Azul índigo oscuro elegante para la cabecera
COLOR_SUBTITULO = "#c7d2fe"         # Lavanda claro para el subtítulo
COLOR_ONLINE = "#34d399"            # Verde esmeralda para el estado "En línea"
COLOR_PENSANDO = "#fbbf24"          # Ámbar para el estado "Escribiendo..."

COLOR_FONDO_CHAT = "#ffffff"        # Blanco puro para la tarjeta del chat
COLOR_BORDE = "#cbd5e1"             # Gris suave para bordes de tarjetas y entradas

COLOR_BURBUJA_USUARIO = "#eff6ff"   # Fondo azul muy suave para mensajes del usuario
COLOR_TITULO_USUARIO = "#1d4ed8"    # Azul intenso para el nombre "Tú"

COLOR_BURBUJA_IA = "#f0fdf4"        # Fondo verde menta suave para respuestas de la IA
COLOR_TITULO_IA = "#047857"         # Verde esmeralda oscuro para "Asistente"

COLOR_BURBUJA_ERROR = "#fef2f2"     # Fondo rojizo suave para avisos de error
COLOR_TITULO_ERROR = "#b91c1c"      # Rojo oscuro para errores

COLOR_BOTON = "#2563eb"             # Azul principal del botón Enviar
COLOR_BOTON_HOVER = "#1d4ed8"       # Azul más oscuro al pasar el ratón por encima
COLOR_CHIP_FONDO = "#e2e8f0"        # Fondo de los botones de preguntas rápidas
COLOR_CHIP_HOVER = "#cbd5e1"        # Hover de los botones de preguntas rápidas
COLOR_TEXTO = "#1e293b"             # Gris carbón para lectura cómoda
COLOR_PLACEHOLDER = "#94a3b8"       # Gris claro para el texto de ayuda del input

TEXTO_PLACEHOLDER = "Escribe tu pregunta aquí (ej: ¿Cuánto cuesta el tinte?)..."
MENSAJE_BIENVENIDA = (
    "🏛️ ¡Hola! Bienvenido/a a Peluquería Antigua Grecia ✨\n"
    "Soy tu oráculo y asistente virtual con IA. Puedes escribir tu consulta abajo o "
    "pulsar uno de los botones rápidos para conocer nuestros servicios, precios y horarios."
)


# ==============================================================================
# 3. LECTURA DEL CONTEXTO DE LA PELUQUERÍA (IN-CONTEXT LEARNING)
# ==============================================================================
def cargar_contexto_servicios(ruta_archivo="servicios.txt"):
    """
    Lee el archivo de texto con los servicios, precios y horarios de la peluquería.
    En lugar de entrenar un modelo desde cero (proceso costoso y lento), usamos
    esta información como contexto (In-Context Learning) dentro del prompt.
    """
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
# 4. COMUNICACIÓN CON LA API DE GEMINI Y MANEJO DE LA RESPUESTA JSON
# ==============================================================================
def consultar_asistente(pregunta_usuario, contexto_peluqueria):
    """
    Construye un prompt delimitado con el contexto de la peluquería, envía la
    consulta a la API de Gemini y procesa el objeto JSON devuelto para extraer
    únicamente el texto limpio de la respuesta.
    """
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
    prompt = f"""Eres el asistente virtual oficial de la 'Peluquería Antigua Grecia'.
Tu única función es responder las dudas de los clientes utilizando EXCLUSIVAMENTE la siguiente información oficial de la peluquería:

--- INICIO DEL CONTEXTO DE LA PELUQUERÍA ---
{contexto_peluqueria}
--- FIN DEL CONTEXTO DE LA PELUQUERÍA ---

Reglas estrictas de comportamiento:
1. Responde de forma amable, clara, breve y directa en español.
2. Basa tus respuestas únicamente en los servicios, precios y horarios indicados en el contexto anterior. No inventes servicios ni precios.
3. Si el usuario pregunta por algo que NO tiene relación con la peluquería o sus servicios (por ejemplo, historia general fuera del salón, matemáticas, programación u otros temas generales), indícale educadamente que solo puedes responder consultas relacionadas con la Peluquería Antigua Grecia.
4. Escribe la respuesta en texto plano (usa viñetas '•' para listas, pero NO uses asteriscos '**' de Markdown) para que se visualice limpia en la ventana de chat.

Pregunta del cliente: {pregunta_usuario}
Respuesta del asistente:"""

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
            modelo = genai.GenerativeModel(nombre_modelo)

            # Enviamos el prompt a la API de Gemini con timeout para evitar bloqueos
            respuesta_api = modelo.generate_content(
                prompt, request_options={"timeout": 12}
            )

            # ------------------------------------------------------------------
            # MANEJO EXPLÍCITO DE LA RESPUESTA EN FORMATO JSON
            # ------------------------------------------------------------------
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

            # Limpiamos posibles asteriscos de Markdown residuales
            texto_limpio = texto_extraido.replace("**", "").strip()
            return texto_limpio

        except KeyError:
            return "⚠️ No se pudo extraer el texto de la respuesta JSON devuelta por la API."
        except Exception as error:
            ultimo_error = error
            continue

    return (
        "⚠️ Error al conectar con la API de Gemini. Comprueba tu conexión a internet "
        f"y que tu API_KEY sea válida.\nDetalle técnico: {ultimo_error}"
    )


# ==============================================================================
# 5. FUNCIONES DE LA INTERFAZ GRÁFICA (TKINTER)
# ==============================================================================
def mostrar_mensaje_en_chat(area_chat, remitente, mensaje, tipo="asistente"):
    """
    Inserta un bloque de mensaje estilizado (tipo tarjeta/burbuja) en el área de chat.
    El widget se mantiene en estado 'disabled' para evitar ediciones manuales.
    """
    area_chat.config(state=tk.NORMAL)

    if tipo == "usuario":
        tag_titulo = "titulo_usuario"
        tag_cuerpo = "cuerpo_usuario"
    elif tipo == "error":
        tag_titulo = "titulo_error"
        tag_cuerpo = "cuerpo_error"
    elif tipo == "bienvenida":
        tag_titulo = "titulo_bienvenida"
        tag_cuerpo = "cuerpo_bienvenida"
    else:
        tag_titulo = "titulo_ia"
        tag_cuerpo = "cuerpo_ia"

    if remitente:
        area_chat.insert(tk.END, f"{remitente}\n", tag_titulo)
    area_chat.insert(tk.END, f"{mensaje}\n", tag_cuerpo)
    area_chat.insert(tk.END, "\n", "espacio")

    # Desplazamos automáticamente el scroll hasta el último mensaje
    area_chat.see(tk.END)
    area_chat.config(state=tk.DISABLED)


def limpiar_historial_chat(area_chat):
    """
    Borra los mensajes anteriores y restaura el mensaje de bienvenida inicial.
    """
    area_chat.config(state=tk.NORMAL)
    area_chat.delete("1.0", tk.END)
    area_chat.config(state=tk.DISABLED)
    mostrar_mensaje_en_chat(
        area_chat, "🏛️ Peluquería Antigua Grecia", MENSAJE_BIENVENIDA, tipo="bienvenida"
    )


def enviar_consulta(
    entrada_usuario,
    area_chat,
    boton_enviar,
    etiqueta_estado,
    ventana,
    contexto_peluqueria,
    pregunta_directa=None,
):
    """
    Recoge la pregunta del usuario (desde el Entry o desde un botón rápido),
    actualiza los indicadores visuales y lanza la consulta en un hilo secundario
    (threading) para que la interfaz nunca se congele.
    """
    if str(boton_enviar["state"]) == tk.DISABLED:
        return

    if pregunta_directa is not None:
        pregunta = pregunta_directa.strip()
    else:
        texto_actual = entrada_usuario.get().strip()
        if not texto_actual or texto_actual == TEXTO_PLACEHOLDER:
            messagebox.showwarning(
                "Campo vacío",
                "Por favor, escribe una pregunta sobre la peluquería antes de pulsar 'Enviar'.",
            )
            return
        pregunta = texto_actual
        entrada_usuario.delete(0, tk.END)

    # 1. Mostramos la pregunta del cliente en el chat
    mostrar_mensaje_en_chat(area_chat, "👤 Tú", pregunta, tipo="usuario")

    # 2. Cambiamos el estado visual del botón y del indicador superior
    boton_enviar.config(state=tk.DISABLED, text="⏳ Pensando...", bg="#94a3b8")
    etiqueta_estado.config(text="● Escribiendo respuesta...", fg=COLOR_PENSANDO)

    # 3. Ejecutamos la petición a la API en segundo plano
    def tarea_en_segundo_plano():
        respuesta_ia = consultar_asistente(pregunta, contexto_peluqueria)
        es_error = respuesta_ia.startswith("⚠️")

        def actualizar_interfaz():
            mostrar_mensaje_en_chat(
                area_chat,
                "💬 Asistente Antigua Grecia",
                respuesta_ia,
                tipo="error" if es_error else "asistente",
            )
            boton_enviar.config(state=tk.NORMAL, text="Enviar ➤", bg=COLOR_BOTON)
            etiqueta_estado.config(text="● En línea", fg=COLOR_ONLINE)
            entrada_usuario.focus()

        ventana.after(0, actualizar_interfaz)

    hilo = threading.Thread(target=tarea_en_segundo_plano, daemon=True)
    hilo.start()


def configurar_placeholder(entrada_usuario):
    """
    Añade un texto de ayuda (placeholder) en gris claro dentro del cuadro de texto
    que desaparece automáticamente al hacer clic para escribir.
    """
    entrada_usuario.insert(0, TEXTO_PLACEHOLDER)
    entrada_usuario.config(fg=COLOR_PLACEHOLDER)

    def al_recibir_foco(evento):
        if entrada_usuario.get() == TEXTO_PLACEHOLDER:
            entrada_usuario.delete(0, tk.END)
            entrada_usuario.config(fg=COLOR_TEXTO)

    def al_perder_foco(evento):
        if not entrada_usuario.get().strip():
            entrada_usuario.insert(0, TEXTO_PLACEHOLDER)
            entrada_usuario.config(fg=COLOR_PLACEHOLDER)

    entrada_usuario.bind("<FocusIn>", al_recibir_foco)
    entrada_usuario.bind("<FocusOut>", al_perder_foco)


def aplicar_efecto_hover(boton, color_normal, color_hover):
    """
    Cambia suavemente el color del botón cuando el ratón pasa por encima.
    """
    boton.bind(
        "<Enter>",
        lambda e: boton.config(bg=color_hover)
        if str(boton["state"]) != tk.DISABLED
        else None,
    )
    boton.bind(
        "<Leave>",
        lambda e: boton.config(bg=color_normal)
        if str(boton["state"]) != tk.DISABLED
        else None,
    )


def iniciar_interfaz():
    """
    Construye y lanza la interfaz gráfica principal con diseño moderno en Tkinter.
    """
    # Activamos nitidez de pantalla (High-DPI) en Windows para que las fuentes se vean nítidas
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    contexto_peluqueria = cargar_contexto_servicios()

    ventana = tk.Tk()
    ventana.title("Peluquería Antigua Grecia — Asistente Virtual IA")
    ventana.geometry("760x640")
    ventana.minsize(580, 480)
    ventana.configure(bg=COLOR_FONDO_APP)

    # --------------------------------------------------------------------------
    # 1. CABECERA SUPERIOR (HEADER DE LA PELUQUERÍA)
    # --------------------------------------------------------------------------
    frame_cabecera = tk.Frame(ventana, bg=COLOR_CABECERA, padx=20, pady=14)
    frame_cabecera.pack(fill=tk.X)

    frame_titulos = tk.Frame(frame_cabecera, bg=COLOR_CABECERA)
    frame_titulos.pack(side=tk.LEFT)

    tk.Label(
        frame_titulos,
        text="🏛️ Peluquería Antigua Grecia ✂️✨",
        font=("Segoe UI", 14, "bold"),
        bg=COLOR_CABECERA,
        fg="#ffffff",
        anchor="w",
    ).pack(anchor="w")

    tk.Label(
        frame_titulos,
        text="Asistente Virtual con IA (Google Gemini)  •  Sin cita previa",
        font=("Segoe UI", 9),
        bg=COLOR_CABECERA,
        fg=COLOR_SUBTITULO,
        anchor="w",
    ).pack(anchor="w", pady=(2, 0))

    # Indicador de estado en tiempo real a la derecha de la cabecera
    etiqueta_estado = tk.Label(
        frame_cabecera,
        text="● En línea",
        font=("Segoe UI", 9, "bold"),
        bg=COLOR_CABECERA,
        fg=COLOR_ONLINE,
    )
    etiqueta_estado.pack(side=tk.RIGHT, anchor="center")

    # --------------------------------------------------------------------------
    # 2. BARRA DE CONSULTAS RÁPIDAS (CHIPS INTERACTIVOS)
    # --------------------------------------------------------------------------
    frame_sugerencias = tk.Frame(ventana, bg=COLOR_FONDO_APP, padx=16, pady=10)
    frame_sugerencias.pack(fill=tk.X)

    tk.Label(
        frame_sugerencias,
        text="Consultas rápidas:",
        font=("Segoe UI", 9, "bold"),
        bg=COLOR_FONDO_APP,
        fg="#475569",
    ).pack(side=tk.LEFT, padx=(0, 8))

    sugerencias = [
        ("💇 Precios de corte", "¿Cuánto cuesta un corte de cabello y un peinado?"),
        ("🎨 Opciones de tinte", "¿Qué opciones de tinte tenéis y cuánto cuestan?"),
        ("🕒 Horarios", "¿Cuál es vuestro horario de atención y abrís los sábados?"),
        ("🧔 Barbería", "¿Qué incluye el servicio de barbería y qué precio tiene?"),
    ]

    # Contenedor del área de chat y de la barra inferior (se declaran antes para los callbacks)
    frame_contenedor_chat = tk.Frame(
        ventana, bg=COLOR_BORDE, padx=1, pady=1
    )
    frame_interior_chat = tk.Frame(frame_contenedor_chat, bg=COLOR_FONDO_CHAT)

    scrollbar = ttk.Scrollbar(frame_interior_chat, orient=tk.VERTICAL)
    area_chat = tk.Text(
        frame_interior_chat,
        wrap=tk.WORD,
        font=("Segoe UI", 10),
        bg=COLOR_FONDO_CHAT,
        fg=COLOR_TEXTO,
        padx=16,
        pady=14,
        relief=tk.FLAT,
        bd=0,
        yscrollcommand=scrollbar.set,
        cursor="arrow",
    )
    scrollbar.config(command=area_chat.yview)

    # Panel inferior de entrada
    frame_inferior = tk.Frame(ventana, bg=COLOR_FONDO_APP, padx=16, pady=12)
    frame_borde_input = tk.Frame(frame_inferior, bg=COLOR_BORDE, padx=1, pady=1)
    frame_input_interno = tk.Frame(frame_borde_input, bg="#ffffff", padx=10, pady=4)

    entrada_usuario = tk.Entry(
        frame_input_interno,
        font=("Segoe UI", 10),
        bg="#ffffff",
        fg=COLOR_TEXTO,
        relief=tk.FLAT,
        bd=0,
    )

    boton_enviar = tk.Button(
        frame_inferior,
        text="Enviar ➤",
        font=("Segoe UI", 10, "bold"),
        bg=COLOR_BOTON,
        fg="#ffffff",
        activebackground=COLOR_BOTON_HOVER,
        activeforeground="#ffffff",
        disabledforeground="#f8fafc",
        relief=tk.FLAT,
        padx=20,
        pady=8,
        cursor="hand2",
    )

    # Creación de los botones de sugerencias rápidas
    for texto_chip, pregunta_chip in sugerencias:
        btn_chip = tk.Button(
            frame_sugerencias,
            text=texto_chip,
            font=("Segoe UI", 9),
            bg=COLOR_CHIP_FONDO,
            fg=COLOR_TEXTO,
            activebackground=COLOR_CHIP_HOVER,
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=lambda p=pregunta_chip: enviar_consulta(
                entrada_usuario,
                area_chat,
                boton_enviar,
                etiqueta_estado,
                ventana,
                contexto_peluqueria,
                pregunta_directa=p,
            ),
        )
        btn_chip.pack(side=tk.LEFT, padx=3)
        aplicar_efecto_hover(btn_chip, COLOR_CHIP_FONDO, COLOR_CHIP_HOVER)

    # Botón para limpiar el chat a la derecha de la barra de sugerencias
    btn_limpiar = tk.Button(
        frame_sugerencias,
        text="🗑️ Limpiar",
        font=("Segoe UI", 9),
        bg=COLOR_CHIP_FONDO,
        fg="#475569",
        activebackground=COLOR_CHIP_HOVER,
        relief=tk.FLAT,
        padx=10,
        pady=3,
        cursor="hand2",
        command=lambda: limpiar_historial_chat(area_chat),
    )
    btn_limpiar.pack(side=tk.RIGHT)
    aplicar_efecto_hover(btn_limpiar, COLOR_CHIP_FONDO, COLOR_CHIP_HOVER)

    # --------------------------------------------------------------------------
    # 3. ÁREA CENTRAL DE CONVERSACIÓN (HISTORIAL CON ESTILO DE TARJETAS)
    # --------------------------------------------------------------------------
    frame_contenedor_chat.pack(padx=16, pady=(0, 4), fill=tk.BOTH, expand=True)
    frame_interior_chat.pack(fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    area_chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Configuración de estilos de bloques de mensaje (burbujas con márgenes y color de fondo)
    area_chat.tag_config(
        "titulo_bienvenida",
        foreground=COLOR_CABECERA,
        background="#f8fafc",
        font=("Segoe UI", 10, "bold"),
        lmargin1=10,
        lmargin2=10,
        rmargin=10,
        spacing1=8,
    )
    area_chat.tag_config(
        "cuerpo_bienvenida",
        foreground="#334155",
        background="#f8fafc",
        font=("Segoe UI", 10),
        lmargin1=10,
        lmargin2=10,
        rmargin=10,
        spacing3=8,
    )
    area_chat.tag_config(
        "titulo_usuario",
        foreground=COLOR_TITULO_USUARIO,
        background=COLOR_BURBUJA_USUARIO,
        font=("Segoe UI", 10, "bold"),
        lmargin1=12,
        lmargin2=12,
        rmargin=12,
        spacing1=8,
    )
    area_chat.tag_config(
        "cuerpo_usuario",
        foreground=COLOR_TEXTO,
        background=COLOR_BURBUJA_USUARIO,
        font=("Segoe UI", 10),
        lmargin1=12,
        lmargin2=12,
        rmargin=12,
        spacing3=8,
    )
    area_chat.tag_config(
        "titulo_ia",
        foreground=COLOR_TITULO_IA,
        background=COLOR_BURBUJA_IA,
        font=("Segoe UI", 10, "bold"),
        lmargin1=12,
        lmargin2=12,
        rmargin=12,
        spacing1=8,
    )
    area_chat.tag_config(
        "cuerpo_ia",
        foreground=COLOR_TEXTO,
        background=COLOR_BURBUJA_IA,
        font=("Segoe UI", 10),
        lmargin1=12,
        lmargin2=12,
        rmargin=12,
        spacing3=8,
    )
    area_chat.tag_config(
        "titulo_error",
        foreground=COLOR_TITULO_ERROR,
        background=COLOR_BURBUJA_ERROR,
        font=("Segoe UI", 10, "bold"),
        lmargin1=12,
        lmargin2=12,
        rmargin=12,
        spacing1=8,
    )
    area_chat.tag_config(
        "cuerpo_error",
        foreground=COLOR_TITULO_ERROR,
        background=COLOR_BURBUJA_ERROR,
        font=("Segoe UI", 10),
        lmargin1=12,
        lmargin2=12,
        rmargin=12,
        spacing3=8,
    )
    area_chat.tag_config("espacio", font=("Segoe UI", 4))

    # Insertamos el mensaje inicial de bienvenida
    limpiar_historial_chat(area_chat)

    # --------------------------------------------------------------------------
    # 4. PANEL INFERIOR (CUADRO DE TEXTO CON PLACEHOLDER Y BOTÓN ENVIAR)
    # --------------------------------------------------------------------------
    frame_inferior.pack(fill=tk.X)

    boton_enviar.config(
        command=lambda: enviar_consulta(
            entrada_usuario,
            area_chat,
            boton_enviar,
            etiqueta_estado,
            ventana,
            contexto_peluqueria,
        )
    )
    boton_enviar.pack(side=tk.RIGHT, padx=(10, 0))
    aplicar_efecto_hover(boton_enviar, COLOR_BOTON, COLOR_BOTON_HOVER)

    frame_borde_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    frame_input_interno.pack(fill=tk.BOTH, expand=True)
    entrada_usuario.pack(fill=tk.BOTH, expand=True, ipady=5)

    configurar_placeholder(entrada_usuario)

    # Permitimos enviar la consulta pulsando la tecla Enter (<Return>)
    entrada_usuario.bind(
        "<Return>",
        lambda evento: enviar_consulta(
            entrada_usuario,
            area_chat,
            boton_enviar,
            etiqueta_estado,
            ventana,
            contexto_peluqueria,
        ),
    )

    ventana.mainloop()


if __name__ == "__main__":
    iniciar_interfaz()
