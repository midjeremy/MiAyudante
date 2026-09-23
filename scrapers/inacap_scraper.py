from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class InacapScraper:
    def __init__(self, driver):
        self.driver = driver
        self.institucion = "INACAP"
        self.url_base = "https://portales.inacap.cl/carreras/index"
        self.urls_a_visitar = set()
        self.datos_carreras = []

    def recolectar_enlaces(self):
        print(f"[{self.institucion}] Explorando catálogo de carreras...")
        self.driver.get(self.url_base)
        
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/carreras/']"))
            )
            elementos = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/carreras/']")
            for elem in elementos:
                href = elem.get_attribute("href")
                if href and "/carreras/" in href and not href.endswith("/carreras/index"):
                    clean_url = href.split("?")[0].rstrip("/")
                    self.urls_a_visitar.add(clean_url)
            print(f"[{self.institucion}] Se encontraron {len(self.urls_a_visitar)} enlaces.")
        except Exception as e:
            print(f"[{self.institucion}] Error recolectando enlaces: {e}")

    def extraer_detalles(self):
        print(f"[{self.institucion}] Extrayendo detalles de {len(self.urls_a_visitar)} carreras...")
        for url in self.urls_a_visitar:
            try:
                self.driver.get(url)
                
                # Título
                try:
                    carrera = self.driver.find_element(By.TAG_NAME, "h1").text.strip()
                except:
                    carrera = "Sin título"

                # Descripción
                try:
                    desc_elem = self.driver.find_element(By.CSS_SELECTOR, "meta[name='description']")
                    descripcion = desc_elem.get_attribute("content") or "Sin descripción"
                except:
                    descripcion = "Sin descripción"

                # Sedes
                sedes = []
                elementos_sedes = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Sede')]")
                for s in elementos_sedes[:6]:
                    txt = s.text.strip()
                    if txt and len(txt) < 40 and txt not in sedes:
                        sedes.append(txt)

                # Malla curricular
                malla_dict = {}
                ramos = self.driver.find_elements(By.CSS_SELECTOR, ".malla li, .asignatura")
                if ramos:
                    malla_dict["Malla General"] = [r.text.strip() for r in ramos if r.text.strip()]
                else:
                    malla_dict = {"Malla": ["Ver detalle en portal INACAP"]}

                self.datos_carreras.append({
                    "institucion": self.institucion,
                    "carrera": carrera,
                    "url_detalle": url,
                    "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "sedes": sedes if sedes else ["Todas las sedes"],
                    "descripcion": descripcion,
                    "malla_url": url,
                    "malla_curricular": malla_dict
                })
            except Exception as e:
                print(f"[{self.institucion}] Error al extraer {url}: {e}")