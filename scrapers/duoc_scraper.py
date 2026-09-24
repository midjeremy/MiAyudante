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
        for _ in range(100):
            try:
                boton_ver_mas = driver.find_elements(By.CSS_SELECTOR, "button.bc-btn-ver-mas")
                if not boton_ver_mas or not boton_ver_mas[0].is_displayed():
                    break

                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton_ver_mas[0])
                driver.execute_script("arguments[0].click();", boton_ver_mas[0])
                time.sleep(0.5)
            except Exception as e:
                print(f"[{self.institucion}] No se pudieron cargar más carreras: {e}")
                break

    def recolectar_enlaces(self, driver):
        print(f"[{self.institucion}] Explorando catálogo completo...")
        self.urls_a_visitar.clear()

        try:
            driver.get(self.url_base)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".bc-card h3 a, a.bc-ver-carrera"))
            )
            time.sleep(1)

            # 1. Procesar pestaña 'Carreras Profesionales'
            print(f"[{self.institucion}] Desplegando Carreras Profesionales...")
            self._cargar_todas_las_tarjetas(driver)

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
                driver.execute_script("arguments[0].click();", pestana_tecnicas[0])
                time.sleep(1)

                self._cargar_todas_las_tarjetas(driver)

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
        self.datos_carreras.clear()
        urls = sorted(self.urls_a_visitar)
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
                    except Exception:
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
                    except Exception:
                        descripcion = "Sin descripción disponible"

                    # 3. Sedes y Aranceles
                    sedes_info = []
                    sedes_nombres = []
                    try:
                        bloques_sedes = driver.find_elements(By.CSS_SELECTOR, "#sedes-y-aranceles .cont-blanco.sedes-aranceles")
                        for bloque in bloques_sedes:
                            nombre_elem = bloque.find_elements(By.CSS_SELECTOR, "h4")
                            nombre = nombre_elem[0].text.replace("SEDE", "").strip() if nombre_elem else ""

                            modalidad_elem = bloque.find_elements(By.CSS_SELECTOR, ".text-justify:not(.cont-gris-claro) p")
                            modalidad = modalidad_elem[0].text.strip() if modalidad_elem else ""

                            arancel_elem = bloque.find_elements(By.CSS_SELECTOR, ".cont-gris-claro p")
                            arancel = arancel_elem[0].text.replace("\n", " | ").strip() if arancel_elem else ""

                            if nombre:
                                if nombre not in sedes_nombres:
                                    sedes_nombres.append(nombre)
                                sedes_info.append({
                                    "sede": nombre,
                                    "modalidad": modalidad,
                                    "costos": arancel
                                })
                    except Exception as e:
                        print(f"Error procesando sedes en {url}: {e}")

                    # 4. Mallas Curriculares Digitales
                    mallas_digitales = []
                    try:
                        # Extraer desde los contenedores dmc-root que contienen data-dmc-src
                        elementos_dmc = driver.find_elements(By.CSS_SELECTOR, ".dmc-root[data-dmc-src]")
                        for el in elementos_dmc:
                            malla_id = el.get_attribute("data-dmc-id") or ""
                            malla_src = el.get_attribute("data-dmc-src") or ""
                            if malla_src and malla_src not in [m["url"] for m in mallas_digitales]:
                                mallas_digitales.append({
                                    "mencion_id": malla_id,
                                    "url": malla_src
                                })

                        # Respaldo: botones en la sección #malla-de-la-carrera
                        if not mallas_digitales:
                            botones_malla = driver.find_elements(By.CSS_SELECTOR, "#malla-de-la-carrera .dmc-abrir-malla a")
                            for btn in botones_malla:
                                href = btn.get_attribute("href")
                                if href:
                                    mallas_digitales.append({
                                        "mencion_id": href.split("#dmc-malla-")[-1] if "#dmc-malla-" in href else "general",
                                        "url": href
                                    })
                    except Exception as e:
                        print(f"Error procesando mallas en {url}: {e}")

                    malla_principal = mallas_digitales[0]["url"] if mallas_digitales else None

                    self.datos_carreras.append({
                        "institucion": self.institucion,
                        "carrera": carrera,
                        "url_detalle": url,
                        "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "sedes": sedes_nombres if sedes_nombres else ["Consultar sedes en portal Duoc"],
                        "detalle_sedes": sedes_info,
                        "descripcion": descripcion,
                        "malla_url": malla_principal,
                        "malla_curricular": {"mallas_digitales": mallas_digitales},
                        "mallas_digitales": mallas_digitales
                    })
                    print(f"[{idx}/{len(urls)}] Duoc UC: {carrera} ({len(sedes_nombres)} sedes, {len(mallas_digitales)} mallas)")

                except Exception as e:
                    print(f"Error procesando {url}: {e}")

                if idx % 20 == 0 and idx < len(urls):
                    print(f"-> [Duoc UC] Liberando memoria RAM...")
                    driver.quit()
                    time.sleep(2)
                    driver = crear_driver()
        finally:
            driver.quit()