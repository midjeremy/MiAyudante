from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def crear_driver():
    opciones = Options()
    opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--disable-gpu")
    opciones.add_argument("--window-size=1920,1080")
    
    # Bloqueo de imágenes para que la navegación sea mucho más rápida
    prefs = {"profile.managed_default_content_settings.images": 2}
    opciones.add_experimental_option("prefs", prefs)
    
    opciones.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=opciones)
    driver.set_page_load_timeout(45)
    driver.implicitly_wait(4)
    return driver