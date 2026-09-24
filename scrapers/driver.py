import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def crear_driver():
    opciones = Options()

    for ruta in (
        os.getenv("CHROME_BINARY"),
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ):
        if ruta and (os.path.exists(ruta) or shutil.which(ruta)):
            opciones.binary_location = ruta
            break

    opciones.page_load_strategy = "eager"
    opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--disable-gpu")
    opciones.add_argument("--disable-software-rasterizer")
    opciones.add_argument("--window-size=1920,1080")

    # Desactivar extensiones y bloquear imágenes para velocidad
    opciones.add_argument("--disable-extensions")
    prefs = {"profile.managed_default_content_settings.images": 2}
    opciones.add_experimental_option("prefs", prefs)

    opciones.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=opciones)
    driver.set_page_load_timeout(45)
    driver.set_script_timeout(30)
    return driver