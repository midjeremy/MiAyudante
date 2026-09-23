import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scrapers.driver import crear_driver

class InacapScraper:
    def __init__(self):
        self.institucion = "INACAP"
        self.url_base = "https://portal.inacap.cl/carreras"
        self.urls_a_visitar = set()
        self.datos_carreras = []

    def recolectar_enlaces(self, driver):
        print(f"[{self.institucion}] Explorando catálogo...")
        driver.get(self.url_base)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/carreras/']"))
            )
            elementos = driver.find_elements(By.CSS_SELECTOR, "a[href*='/carreras/']")
            for elem in elementos:
                href = elem.get_attribute("href")
                if href and "/carreras/" in href:
                    clean_url = href.split("?")[0].rstrip("/")
                    if not any(clean_url.endswith(x) for x in ["/carreras", "/index", "/carreras#"]):
                        if "/area-" in clean_url or len(clean_url.split("/")) > 4:
                            self.urls_a_visitar.add(clean_url)
            print(f"[{self.institucion}] Se encontraron {len(self.urls_a_visitar)} carreras únicas.")
        except Exception as e:
            print(f"[{self.institucion}] Error recolectando enlaces: {e}")

    def extraer_detalles(self):
        print(f"[{self.institucion}] Extrayendo detalles de {len(self.urls_a_visitar)} carreras...")
        urls = list(self.urls_a_visitar)
        driver = crear_driver()
        
        try:
            for idx, url in enumerate(urls, 1):
                try:
                    driver.get(url)
                    
                    # 1. Nombre de la Carrera
                    try:
                        WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.component-heading, h1"))
                        )
                        carrera = driver.find_element(By.CSS_SELECTOR, "h1.component-heading, h1").text.strip()
                    except:
                        carrera = "Carrera INACAP"

                    # 2. Descripción desde acordeón
                    descripcion = ""
                    try:
                        elem_desc = driver.find_elements(By.CSS_SELECTOR, "#descripcion .interior-panel, .parrafo-acrodeon-carreras")
                        if elem_desc and elem_desc[0].text.strip():
                            descripcion = elem_desc[0].text.strip()
                        else:
                            desc_meta = driver.find_element(By.CSS_SELECTOR, "meta[name='description']")
                            descripcion = desc_meta.get_attribute("content") or "Sin descripción disponible"
                    except:
                        descripcion = "Sin descripción disponible"

                    # 3. Malla PDF
                    malla_url = url
                    try:
                        pdf_btn = driver.find_elements(By.CSS_SELECTOR, "a[href*='pdf_mallas'], a[href*='MallaCurricular']")
                        if pdf_btn:
                            malla_url = pdf_btn[0].get_attribute("href")
                    except:
                        pass

                    # 4. Sedes
                    sedes = []
                    try:
                        elementos_sedes = driver.find_elements(By.CSS_SELECTOR, ".sidebarCarrera__sedes .interior-panel, #sedes-imparten-carrera .interior-panel")
                        if elementos_sedes and elementos_sedes[0].text.strip():
                            sedes = [s.strip() for s in elementos_sedes[0].text.split("\n") if s.strip()]
                        if not sedes:
                            btn_sedes = driver.find_elements(By.CSS_SELECTOR, ".btn_sede p")
                            for bs in btn_sedes:
                                txt = bs.text.strip()
                                if txt and txt not in sedes:
                                    sedes.append(txt)
                    except:
                        pass
                    if not sedes:
                        sedes = ["Campus Digital / Sedes a nivel nacional"]

                    self.datos_carreras.append({
                        "institucion": self.institucion,
                        "carrera": carrera,
                        "url_detalle": url,
                        "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "sedes": sedes,
                        "descripcion": descripcion,
                        "malla_url": malla_url,
                        "malla_curricular": {"malla_pdf": malla_url}
                    })
                    print(f"[{idx}/{len(urls)}] INACAP: {carrera}")
                except Exception as e:
                    print(f"Error procesando {url}: {e}")

                # Liberación de memoria cada 20 visitas
                if idx % 20 == 0 and idx < len(urls):
                    print(f"-> [INACAP] Reiniciando navegador para liberar memoria RAM...")
                    driver.quit()
                    time.sleep(2)
                    driver = crear_driver()
        finally:
            driver.quit()