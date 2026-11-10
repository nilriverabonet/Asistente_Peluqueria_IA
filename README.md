# Asistente Virtual para una Peluquería con IA (Google Gemini + Tkinter)

Aplicación de escritorio en Python con interfaz gráfica (**Tkinter**) que actúa como asistente virtual de la **Peluquería Brillo Estelar**, respondiendo consultas sobre servicios, precios y horarios mediante la **API de Google Gemini** y el uso de contexto (*In-Context Learning*).

---

## 📋 Requisitos e Instalación

1. Asegúrate de tener Python 3.10 o superior instalado.
2. Instala las dependencias del proyecto ejecutando:

```bash
pip install -r requirements.txt
```

3. Configura tu clave de API de Google Gemini en el archivo `.env` (en la raíz del proyecto):

```env
API_KEY=tu_clave_api_aqui
```

*(Nota: El archivo `.env` está incluido en `.gitignore` para no exponer la clave en repositorios públicos).*

---

## 🚀 Ejecución

Ejecuta el asistente desde la raíz del proyecto:

```bash
python asistente_gui.py
```

---

## 📁 Estructura del Proyecto

```text
PrDesafio02_Asistente_Peluqueria_IA/
├── asistente_gui.py   # Interfaz gráfica con Tkinter, conexión a Gemini y manejo de JSON
├── servicios.txt      # Contexto con los servicios, precios y horarios de la peluquería
├── requirements.txt   # Dependencias del proyecto (google-generativeai, python-dotenv)
├── .gitignore         # Exclusión del archivo .env y entorno virtual en Git
└── README.md          # Documentación del proyecto
```

