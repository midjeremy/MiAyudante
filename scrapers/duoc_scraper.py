from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class DuocScraper:
    def __init__(self, driver):
        self.driver = driver
        self.institucion = "Duoc UC"
        self.url_base = "https://www.duoc.cl/carreras/"
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
                if href and href != self.url_base and "/carreras/" in href:
                    clean_url = href.split("?")[0].rstrip("/")
                    # Evitar rutas genéricas que no sean fichas técnicas
                    if not clean_url.endswith("/carreras"):
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
                elementos_sedes = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Sede') or contains(text(), 'Campus')]")
                for s in elementos_sedes[:5]:
                    txt = s.text.strip()
                    if txt and len(txt) < 40 and txt not in sedes:
                        sedes.append(txt)

                # Malla curricular
                malla_dict = {}
                semestres = self.driver.find_elements(By.CSS_SELECTOR, ".semestre, [class*='semester']")
                if semestres:
                    for idx, sem in enumerate(semestres, 1):
                        ramos = [r.text.strip() for r in sem.find_elements(By.TAG_NAME, "li") if r.text.strip()]
                        malla_dict[f"Semestre {idx}"] = ramos
                else:
                    malla_dict = {"Malla": ["Consultar en portal web"]}

                self.datos_carreras.append({
                    "institucion": self.institucion,
                    "carrera": carrera,
                    "url_detalle": url,
                    "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "sedes": sedes if sedes else ["Información en web"],
                    "descripcion": descripcion,
                    "malla_url": url,
                    "malla_curricular": malla_dict
                })
            except Exception as e:
                print(f"[{self.institucion}] Error al extraer {url}: {e}")