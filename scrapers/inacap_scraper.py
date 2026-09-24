import time
from datetime import datetime
from selenium.common.exceptions import TimeoutException, WebDriverException
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
        self.urls_a_visitar.clear()
        try:
            driver.get(self.url_base)
            WebDriverWait(driver, 10).until(
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

    def _extraer_malla_interactiva(self, driver, url_malla):
        """Navega a la URL de la malla en SIGA y extrae asignaturas por semestre."""
        semestres = []
        try:
            driver.get(url_malla)
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#tblPrincipal td.tarjeta .font-asignatura"))
            )

            # Cabeceras de semestres
            th_elems = driver.find_elements(By.CSS_SELECTOR, "#tblPrincipal tbody tr:first-child td h4")
            nombres_semestres = [th.text.strip() for th in th_elems if th.text.strip()]
            num_cols = len(nombres_semestres)

            if num_cols == 0:
                return {}

            mapa_semestres = {i: {"semestre": nombres_semestres[i], "asignaturas": []} for i in range(num_cols)}

            # Filas de asignaturas
            filas_datos = driver.find_elements(By.CSS_SELECTOR, "#tblPrincipal tbody tr")
            for fila in filas_datos:
                # Omitir filas de cabecera y totales de horas
                if fila.find_elements(By.CSS_SELECTOR, ".card-hrs"):
                    continue

                tds = fila.find_elements(By.XPATH, "./td")
                if len(tds) < num_cols:
                    continue

                for col_idx in range(num_cols):
                    td = tds[col_idx]
                    tarjetas = td.find_elements(By.CSS_SELECTOR, "td.tarjeta")
                    for card in tarjetas:
                        nombre_elem = card.find_elements(By.CSS_SELECTOR, ".font-asignatura")
                        codigo_elem = card.find_elements(By.CSS_SELECTOR, ".font-codigo")

                        nombre = nombre_elem[0].text.strip() if nombre_elem else ""
                        codigo = codigo_elem[0].text.strip() if codigo_elem else ""

                        if nombre:
                            asig_dict = {"nombre": nombre}
                            if codigo:
                                asig_dict["codigo"] = codigo
                            mapa_semestres[col_idx]["asignaturas"].append(asig_dict)

            semestres = [mapa_semestres[i] for i in range(num_cols) if mapa_semestres[i]["asignaturas"]]
        except Exception as e:
            print(f"[{self.institucion}] Advertencia extrayendo malla interactiva: {e}")

        return {"semestres": semestres} if semestres else {}

    def extraer_detalles(self):
        print(f"[{self.institucion}] Extrayendo detalles de {len(self.urls_a_visitar)} carreras...")
        self.datos_carreras.clear()
        urls = sorted(self.urls_a_visitar)
        driver = crear_driver()

        try:
            for idx, url in enumerate(urls, 1):
                try:
                    driver.get(url)

                    # 1. Nombre de la Carrera
                    try:
                        WebDriverWait(driver, 6).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.component-heading, h1"))
                        )
                        carrera = driver.find_element(By.CSS_SELECTOR, "h1.component-heading, h1").text.strip() or "Carrera INACAP"
                    except Exception:
                        carrera = "Carrera INACAP"

                    # 2. Datos generales (Título, Duración, Requisitos)
                    titulo_otorgado = ""
                    duracion = ""
                    requisitos_ingreso = ""

                    try:
                        tit_el = driver.find_elements(By.CSS_SELECTOR, "#btncarrera span.tit-pro")
                        if tit_el:
                            titulo_otorgado = tit_el[0].text.replace("Título:", "").strip()

                        dur_el = driver.find_elements(By.CSS_SELECTOR, "#btncarrera span.duracion")
                        if dur_el:
                            duracion = dur_el[0].text.replace("Duración:", "").strip()

                        req_el = driver.find_elements(By.CSS_SELECTOR, ".msn-rojo p")
                        if req_el:
                            requisitos_ingreso = req_el[0].text.replace("Requisitos de ingreso:", "").strip()
                    except Exception:
                        pass

                    # 3. Descripción
                    descripcion = ""
                    try:
                        elem_desc = driver.find_elements(By.CSS_SELECTOR, "#descripcion .interior-panel, .parrafo-acrodeon-carreras")
                        if elem_desc and elem_desc[0].text.strip():
                            descripcion = elem_desc[0].text.strip()
                        else:
                            desc_meta = driver.find_element(By.CSS_SELECTOR, "meta[name='description']")
                            descripcion = desc_meta.get_attribute("content") or "Sin descripción disponible"
                    except Exception:
                        descripcion = "Sin descripción disponible"

                    # 4. Enlaces de Malla (PDF e Interactiva SIGA)
                    malla_pdf_url = None
                    malla_digital_url = ""
                    try:
                        pdf_btn = driver.find_elements(By.CSS_SELECTOR, "a[href*='pdf_mallas'], a.btn-descargar a")
                        if pdf_btn:
                            malla_pdf_url = pdf_btn[0].get_attribute("href")

                        digital_btn = driver.find_elements(By.CSS_SELECTOR, "a[href*='MallaCurricular'], a.btn-digital a")
                        if digital_btn:
                            malla_digital_url = digital_btn[0].get_attribute("href")
                    except Exception:
                        pass

                    # 5. Sedes que imparten la carrera
                    sedes = []
                    try:
                        elementos_sedes = driver.find_elements(
                            By.CSS_SELECTOR, 
                            ".sidebarCarrera__sedes .interiorCarrera-sede .btn_sede p, .sidebarCarrera__sedes .interior-panel .btn_sede p"
                        )
                        for s in elementos_sedes:
                            txt = s.text.strip()
                            if txt and txt not in sedes:
                                sedes.append(txt)

                        if not sedes:
                            # Respaldo para selectores alternativos
                            fallback_sedes = driver.find_elements(By.CSS_SELECTOR, ".btn_sede p")
                            for bs in fallback_sedes:
                                txt = bs.text.strip()
                                if txt and txt not in sedes:
                                    sedes.append(txt)
                    except Exception:
                        pass

                    if not sedes:
                        sedes = ["Campus Digital / Sedes a nivel nacional"]

                    # 6. Extracción de Malla Curricular Estructurada
                    malla_curricular = {}
                    if malla_pdf_url:
                        malla_curricular["malla_pdf"] = malla_pdf_url
                    if malla_digital_url:
                        malla_curricular["malla_digital_url"] = malla_digital_url
                        datos_malla = self._extraer_malla_interactiva(driver, malla_digital_url)
                        if datos_malla.get("semestres"):
                            malla_curricular["semestres"] = datos_malla["semestres"]

                    self.datos_carreras.append({
                        "institucion": self.institucion,
                        "carrera": carrera,
                        "titulo_otorgado": titulo_otorgado,
                        "duracion": duracion,
                        "requisitos_ingreso": requisitos_ingreso,
                        "url_detalle": url,
                        "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "sedes": sedes,
                        "descripcion": descripcion,
                        "malla_url": malla_pdf_url,
                        "malla_curricular": malla_curricular
                    })
                    print(f"[{idx}/{len(urls)}] INACAP: {carrera}")

                except (TimeoutException, WebDriverException) as e:
                    print(f"[INACAP] Timeout o error en página: {url} -> {e}")
                    continue
                except Exception as e:
                    print(f"Error procesando {url}: {e}")

                # Liberar RAM cada 20 registros
                if idx % 20 == 0 and idx < len(urls):
                    print(f"-> [INACAP] Reiniciando navegador para liberar memoria RAM...")
                    driver.quit()
                    time.sleep(2)
                    driver = crear_driver()
        finally:
            driver.quit()