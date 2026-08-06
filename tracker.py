# Importar librerías nativas y de terceros para automatización y parseo web
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
import requests

# --- NUEVAS LIBRERÍAS PARA GOOGLE SHEETS ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials

print("Iniciando el Rastreador de Precios de mercado libre")
print("-" * 50)

# --- CONFIGURACIÓN DE TELEGRAM ---
TELEGRAM_TOKEN = "8742532941:AAEfpjN2dqKGwdmr_MdyPrc7MHcEhjsmFK0"
TELEGRAM_CHAT_ID = "8868703501"
mensaje_alerta = "🤖 *Reporte de Precios Mercado Libre*\n\n"

# --- AUTENTICACIÓN EN GOOGLE SHEETS ---
print("Conectando a la base de datos en Google Sheets...")
# Definir los permisos (Scopes) que necesita el bot
alcance = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

# Cargar las credenciales desde el archivo JSON local
credenciales = ServiceAccountCredentials.from_json_keyfile_name(
    "clave_privada_para_pricetrackerbot_en_google_cloud.json", alcance)
cliente = gspread.authorize(credenciales)

# Abrir el documento por su nombre exacto y seleccionar la primera hoja
hoja_calculo = cliente.open("Historial_Precios_pricetrackerbot").sheet1

# Escribir encabezados si la hoja está vacía (comprueba si la fila 1 tiene datos)
if not hoja_calculo.row_values(1):
    hoja_calculo.append_row(
        ["Fecha_Hora", "Producto", "Precio", "Opciones_Pago"])

print("✅ Conexión exitosa. Iniciando extracción...\n")

# Definir el diccionario de productos objetivo
productos = {
    "DJI Neo 2": "https://www.mercadolibre.com.mx/dji-pack-neo-2-vuela-mas-con-control-remoto-rc-n3-transmision-estable-con-transceptor-digital-dron-4k-para-principiantes-3-baterias/p/MLM62050547",
    "Insta360 GO Ultra": "https://www.mercadolibre.com.mx/camara-de-accion-insta360-go-ultra-creator-bundle-4k-negro/up/MLMU3859446686",
    "Insta360 X5": "https://www.mercadolibre.com.mx/camara-de-accion-insta360-x5-motorcycle-bundle-negro/up/MLMU3866394527"
}

# Configurar parámetros avanzados del WebDriver
opciones = webdriver.ChromeOptions()
opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
opciones.add_experimental_option('useAutomationExtension', False)
opciones.add_argument("--disable-blink-features=AutomationControlled")
opciones.add_argument("--start-maximized")
opciones.add_argument("--headless=new")

servicio = Service(ChromeDriverManager().install())
navegador = webdriver.Chrome(service=servicio, options=opciones)

# Iniciar el procesamiento por lotes (Batch Processing)
for nombre, enlace in productos.items():
    print(f"Analizando métricas de: {nombre}...")
    navegador.get(enlace)
    time.sleep(5)

    html_crudo = navegador.page_source
    sopa = BeautifulSoup(html_crudo, 'html.parser')

    precio_final = "No encontrado"
    texto_limpio = "Sin promoción"

    # Aislar y extraer el precio
    meta_precio = sopa.find('meta', itemprop='price')

    if meta_precio:
        # Extraemos el valor del atributo 'content' (ej. "8819.00")
        precio_texto = meta_precio.get('content')
        # Lo convertimos primero a decimal (float) por si tiene centavos, y luego a entero (int)
        precio_final = int(float(precio_texto))
        print(f"- Precio actual: ${precio_final:,}")
    else:
        print("- No se encontró el precio en los metadatos.")

    # Aislar opciones de financiamiento
    meses_elemento = sopa.find('span', string=re.compile(
        "meses sin intereses", re.IGNORECASE))
    if meses_elemento:
        texto_limpio = meses_elemento.text.strip().replace(" de", "")
        print(f"- Opciones de pago: {texto_limpio}")
    else:
        print("- Sin promoción de meses sin intereses.")

    # Agregar los datos al bloque de Telegram
    mensaje_alerta += f"📦 *{nombre}*\n💰 Precio: ${precio_final:,}\n💳 Pago: {texto_limpio}\n🔗 [Ir a la tienda]({enlace})\n\n"

    # --- GUARDAR EN GOOGLE SHEETS ---
    # Enviamos los datos directamente a la nube como una nueva fila
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hoja_calculo.append_row([fecha_actual, nombre, precio_final, texto_limpio])
    print(f"✅ Datos guardados en la nube para {nombre}.\n")

    time.sleep(5)

navegador.quit()

# --- ENVÍO DE DATOS A TELEGRAM ---
print("-" * 50)
print("Transmitiendo datos a dispositivo móvil vía API REST...")
url_api_telegram = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
payload = {
    "chat_id": TELEGRAM_CHAT_ID,
    "text": mensaje_alerta,
    "parse_mode": "Markdown"
}
respuesta = requests.post(url_api_telegram, data=payload)

if respuesta.status_code == 200:
    print("✅ ¡Mensaje entregado exitosamente a Telegram!")
else:
    print(
        f"❌ Error al enviar el mensaje. Código HTTP: {respuesta.status_code}")

print("Extracción y almacenamiento en la nube finalizados exitosamente.")
