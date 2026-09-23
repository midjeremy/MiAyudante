import shutil

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options


def crear_driver():
    opciones = Options()
    opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--disable-gpu")
    opciones.add_argument("--window-size=1280,720")
    opciones.add_argument("--disable-extensions")
    opciones.add_argument("--disable-infobars")
    opciones.add_argument("--disable-blink-features=AutomationControlled")
    opciones.add_argument("--disable-background-networking")
    opciones.add_argument("--disable-default-apps")
    opciones.add_argument("--no-first-run")
    opciones.add_argument("--mute-audio")
    opciones.add_argument("--disable-software-rasterizer")
    opciones.add_argument("--remote-debugging-pipe")
    opciones.page_load_strategy = "eager"

    # Permite trabajar con las rutas habituales de Chrome/Chromium en EC2.
    navegador = next(
        (
            ruta
            for ruta in (
                shutil.which("google-chrome"),
                shutil.which("google-chrome-stable"),
                shutil.which("chromium"),
                shutil.which("chromium-browser"),
            )
            if ruta
        ),
        None,
    )
    if navegador:
        opciones.binary_location = navegador

    # Bloquear descarga de imágenes para ahorrar CPU y RAM
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "disk-cache-size": 4096
    }
    opciones.add_experimental_option("prefs", prefs)
    opciones.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        driver = webdriver.Chrome(options=opciones)
    except WebDriverException as error:
        raise RuntimeError(
            "No se pudo iniciar Chrome/Chromium. En EC2 instala un navegador compatible "
            "(por ejemplo, chromium) y verifica que Selenium Manager tenga acceso a Internet. "
            f"Detalle original: {error}"
        ) from error

    driver.set_page_load_timeout(20)
    driver.set_script_timeout(20)
    driver.implicitly_wait(2)
    return driver