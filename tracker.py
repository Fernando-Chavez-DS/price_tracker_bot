# Importar librerías nativas y de terceros para automatización y parseo web
import undetected_chromedriver as uc
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
alcance = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

credenciales = ServiceAccountCredentials.from_json_keyfile_name(
    "clave_privada_para_pricetrackerbot_en_google_cloud.json", alcance)
cliente = gspread.authorize(credenciales)

hoja_calculo = cliente.open("Historial_Precios_pricetrackerbot").sheet1

if not hoja_calculo.row_values(1):
    hoja_calculo.append_row(
        ["Fecha_Hora", "Producto", "Precio", "Opciones_Pago"])

print("✅ Conexión exitosa. Iniciando extracción...\n")

productos = {
    "DJI Neo 2": "https://www.mercadolibre.com.mx/dji-pack-neo-2-vuela-mas-con-control-remoto-rc-n3-transmision-estable-con-transceptor-digital-dron-4k-para-principiantes-3-baterias/p/MLM62050547",
    "Insta360 GO Ultra": "https://www.mercadolibre.com.mx/camara-de-accion-insta360-go-ultra-creator-bundle-4k-negro/up/MLMU3859446686",
    "Insta360 X5": "https://www.mercadolibre.com.mx/camara-de-accion-insta360-x5-motorcycle-bundle-negro/up/MLMU3866394527"
}

# --- NUEVA CONFIGURACIÓN ANTIBLOQUEO (UNDETECTED CHROMEDRIVER) ---
opciones = uc.ChromeOptions()
opciones.add_argument("--start-maximized")

# El modo fantasma sigue comentado para que veas la magia en tu pantalla local
# opciones.add_argument("--headless=new")

print("Arrancando navegador indetectable...")
# Inicializamos el navegador con las defensas activadas
navegador = uc.Chrome(options=opciones, version_main=150)

for nombre, enlace in productos.items():
    print(f"Analizando métricas de: {nombre}...")
    navegador.get(enlace)
    # Le damos un poco más de tiempo para que cargue como un humano normal
    time.sleep(15)

    html_crudo = navegador.page_source
    sopa = BeautifulSoup(html_crudo, 'html.parser')
    print(f"🕵️ Pista de depuración - Título de la ventana: {navegador.title}")
    precio_final = "No encontrado"
    texto_limpio = "Sin promoción"

    meta_precio = sopa.find('meta', itemprop='price')

    if meta_precio:
        precio_texto = meta_precio.get('content')
        precio_numero = int(float(precio_texto))
        precio_final = f"${precio_numero:,}"
        print(f"- Precio actual: {precio_final}")
    else:
        precio_final = "No encontrado"
        print("- No se encontró el precio en los metadatos.")

    meses_elemento = sopa.find('span', string=re.compile(
        "meses sin intereses", re.IGNORECASE))

    if meses_elemento:
        texto_limpio = meses_elemento.text.strip().replace(" de", "")
        print(f"- Opciones de pago: {texto_limpio}")
    else:
        print("- Sin promoción de meses sin intereses.")

    mensaje_alerta += f"📦 *{nombre}*\n💰 Precio: {precio_final}\n💳 Pago: {texto_limpio}\n🔗 [Ir a la tienda]({enlace})\n\n"

    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hoja_calculo.append_row([fecha_actual, nombre, precio_final, texto_limpio])
    print(f"✅ Datos guardados en la nube para {nombre}.\n")

    time.sleep(5)

navegador.quit()

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

print("Extracción y almacenamiento finalizados exitosamente.")
