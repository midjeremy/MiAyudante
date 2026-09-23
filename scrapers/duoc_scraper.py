import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scrapers.driver import crear_driver

class DuocScraper:
    def __init__(self):
        self.institucion = "Duoc UC"
        self.url_base = "https://www.duoc.cl/oferta-academica/carreras/"
        self.urls_a_visitar = set()
        self.datos_carreras = []

    def _cargar_todas_las_tarjetas(self, driver):
        """Hace clic iterativo en 'Ver más resultados' hasta desplegar todas las carreras de la vista."""
        while True:
            try:
                # Buscar el botón 'Ver más resultados'
                boton_ver_mas = driver.find_elements(By.CSS_SELECTOR, "button.bc-btn-ver-mas")
                if not boton_ver_mas or not boton_ver_mas[0].is_displayed():
                    break

                # Desplazar la vista y hacer clic mediante JavaScript para evitar bloqueos
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton_ver_mas[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", boton_ver_mas[0])
                time.sleep(2)
            except Exception:
                break

    def recolectar_enlaces(self, driver):
        print(f"[{self.institucion}] Explorando catálogo completo...")
        self.urls_a_visitar.clear()

        try:
            driver.get(self.url_base)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".bc-card h3 a, a.bc-ver-carrera"))
            )
            time.sleep(2)

            # 1. Procesar pestaña 'Carreras Profesionales' (activa por defecto)
            print(f"[{self.institucion}] Desplegando Carreras Profesionales...")
            self._cargar_todas_las_tarjetas(driver)

            # Recolectar enlaces del primer lote
            cards = driver.find_elements(By.CSS_SELECTOR, ".bc-card h3 a, a.bc-ver-carrera")
            for elem in cards:
                href = elem.get_attribute("href")
                if href and "/carreras/" in href:
                    clean_url = href.split("?")[0].rstrip("/")
                    if not clean_url.endswith("/carreras") and not clean_url.endswith("duoc.cl"):
                        self.urls_a_visitar.add(clean_url)
            print(f"[{self.institucion}] Profesionales cargadas. Subtotal acumulado: {len(self.urls_a_visitar)}")

            # 2. Cambiar a la pestaña 'Carreras Técnicas'
            pestana_tecnicas = driver.find_elements(By.CSS_SELECTOR, "button.bc-tab[data-tipo='Técnica']")
            if pestana_tecnicas:
                print(f"[{self.institucion}] Cambiando a pestaña de Carreras Técnicas...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pestana_tecnicas[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", pestana_tecnicas[0])
                time.sleep(3)

                # Desplegar todas las técnicas con el botón 'Ver más'
                self._cargar_todas_las_tarjetas(driver)

                # Recolectar enlaces del segundo lote
                cards_tec = driver.find_elements(By.CSS_SELECTOR, ".bc-card h3 a, a.bc-ver-carrera")
                for elem in cards_tec:
                    href = elem.get_attribute("href")
                    if href and "/carreras/" in href:
                        clean_url = href.split("?")[0].rstrip("/")
                        if not clean_url.endswith("/carreras") and not clean_url.endswith("duoc.cl"):
                            self.urls_a_visitar.add(clean_url)

            print(f"[{self.institucion}] Total de carreras encontradas en Duoc UC: {len(self.urls_a_visitar)}")
        except Exception as e:
            print(f"[{self.institucion}] Error recolectando catálogo: {e}")

    def extraer_detalles(self):
        print(f"[{self.institucion}] Extrayendo detalles de {len(self.urls_a_visitar)} carreras...")
        urls = list(self.urls_a_visitar)
        driver = crear_driver()

        try:
            for idx, url in enumerate(urls, 1):
                try:
                    driver.get(url)

                    # 1. Título
                    try:
                        WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.name, h1"))
                        )
                        carrera = driver.find_element(By.CSS_SELECTOR, "h1.name, h1").text.strip().split("\n")[0].strip() or "Carrera Duoc UC"
                    except:
                        carrera = "Carrera Duoc UC"

                    # 2. Descripción
                    descripcion = ""
                    try:
                        textos = driver.find_elements(By.CSS_SELECTOR, ".texto-box-carrera p")
                        if textos:
                            descripcion = "\n".join([p.text.strip() for p in textos if p.text.strip()])
                        else:
                            desc_meta = driver.find_element(By.CSS_SELECTOR, "meta[name='description']")
                            descripcion = desc_meta.get_attribute("content") or "Sin descripción disponible"
                    except:
                        descripcion = "Sin descripción disponible"

                    # 3. Sedes
                    sedes = []
                    try:
                        bloques_sedes = driver.find_elements(By.CSS_SELECTOR, ".sedes-aranceles h4, .grid .card h3")
                        for s in bloques_sedes:
                            nombre_sede = s.text.replace("SEDE", "").strip()
                            if nombre_sede and nombre_sede not in sedes:
                                sedes.append(nombre_sede)
                    except:
                        pass
                    if not sedes:
                        sedes = ["Consultar sedes en portal Duoc"]

                    # 4. Malla Curricular
                    malla_dict = {}
                    malla_url = url
                    elementos_malla = driver.find_elements(By.CSS_SELECTOR, "[data-dmc-src]")
                    if elementos_malla:
                        malla_url = elementos_malla[0].get_attribute("data-dmc-src")
                        malla_dict["Menciones"] = [m.get_attribute("data-dmc-id") for m in elementos_malla if m.get_attribute("data-dmc-id")]
                    else:
                        malla_dict["Detalle"] = ["Consultar malla en portal"]

                    self.datos_carreras.append({
                        "institucion": self.institucion,
                        "carrera": carrera,
                        "url_detalle": url,
                        "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "sedes": sedes,
                        "descripcion": descripcion,
                        "malla_url": malla_url,
                        "malla_curricular": malla_dict
                    })
                    print(f"[{idx}/{len(urls)}] Duoc UC: {carrera}")
                except Exception as e:
                    print(f"Error procesando {url}: {e}")

                # Liberación periódica de RAM en t3.small
                if idx % 20 == 0 and idx < len(urls):
                    print(f"-> [Duoc UC] Liberando memoria RAM...")
                    driver.quit()
                    time.sleep(2)
                    driver = crear_driver()
        finally:
            driver.quit()
