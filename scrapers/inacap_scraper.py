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
            WebDriverWait(driver, 12).until(
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

    def _extraer_malla_siga_inacap(self, driver, url_siga):
        """Navega al visor SIGA y extrae los semestres en el formato: 'ASIGNATURA - CÓDIGO'."""
        try:
            driver.get(url_siga)
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#tblPrincipal"))
            )
            time.sleep(1.5)

            # Extraer columnas y asignaturas directamente desde el DOM mediante JavaScript
            script = """
            var result = {};
            var table = document.querySelector('#tblPrincipal');
            if (!table) return result;

            var headerCells = table.querySelectorAll('tr:first-child .semestre h4');
            var headers = [];
            for (var i = 0; i < headerCells.length; i++) {
                headers.push(headerCells[i].innerText.trim());
            }

            var allCells = table.querySelectorAll('td[ng-repeat="item in item"]');
            if (headers.length === 0 || allCells.length === 0) return result;

            for (var i = 0; i < allCells.length; i++) {
                var colIdx = i % headers.length;
                var semName = headers[colIdx];
                if (!result[semName]) result[semName] = [];

                var tarjetas = allCells[i].querySelectorAll('.tarjeta');
                for (var t = 0; t < tarjetas.length; t++) {
                    var asigEl = tarjetas[t].querySelector('.font-asignatura');
                    var codEl = tarjetas[t].querySelector('.font-codigo');
                    var asig = asigEl ? asigEl.innerText.trim() : '';
                    var cod = codEl ? codEl.innerText.trim() : '';
                    if (asig && cod) {
                        var itemStr = asig + ' - ' + cod;
                        if (result[semName].indexOf(itemStr) === -1) {
                            result[semName].push(itemStr);
                        }
                    }
                }
            }
            return result;
            """
            data_malla = driver.execute_script(script)
            if data_malla and isinstance(data_malla, dict):
                # Filtrar semestres vacíos
                return {k: v for k, v in data_malla.items() if len(v) > 0}
        except Exception as e:
            print(f"[{self.institucion}] Advertencia extrayendo malla SIGA: {e}")

        return {}

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
                            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.component-heading, h1"))
                        )
                        carrera = driver.find_element(By.CSS_SELECTOR, "h1.component-heading, h1").text.strip() or "Carrera INACAP"
                    except Exception:
                        carrera = "Carrera INACAP"

                    # 2. Descripción
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

                    # 3. Malla digital (SIGA) y PDF
                    malla_url = url
                    url_malla_siga = ""
                    try:
                        siga_btn = driver.find_elements(By.CSS_SELECTOR, "a[href*='MallaCurricular'], a.btn-digital a")
                        if siga_btn:
                            url_malla_siga = siga_btn[0].get_attribute("href")

                        pdf_btn = driver.find_elements(By.CSS_SELECTOR, "a[href*='pdf_mallas'], a.btn-descargar a")
                        if pdf_btn:
                            malla_url = pdf_btn[0].get_attribute("href")
                    except Exception:
                        pass

                    # Si hay enlace a SIGA, esa es la URL principal de la malla mostrada en carreras_completas.json
                    if url_malla_siga:
                        malla_url = url_malla_siga

                    # 4. Sedes (Lista limpia de nombres de sedes)
                    sedes = []
                    try:
                        elementos_sedes = driver.find_elements(
                            By.CSS_SELECTOR, 
                            ".sidebarCarrera__sedes .interiorCarrera-sede .btn_sede p, .sidebarCarrera__sedes .interior-panel .btn_sede p"
                        )
                        for s in elementos_sedes:
                            txt = s.text.strip().title()
                            if txt and txt not in sedes:
                                sedes.append(txt)

                        if not sedes:
                            fallback_sedes = driver.find_elements(By.CSS_SELECTOR, ".btn_sede p")
                            for bs in fallback_sedes:
                                txt = bs.text.strip().title()
                                if txt and txt not in sedes:
                                    sedes.append(txt)
                    except Exception:
                        pass

                    if not sedes:
                        sedes = ["Campus Digital", "Sedes A Nivel Nacional"]

                    # 5. Malla Curricular
                    malla_curricular = {}
                    if url_malla_siga:
                        malla_curricular = self._extraer_malla_siga_inacap(driver, url_malla_siga)

                    self.datos_carreras.append({
                        "institucion": self.institucion,
                        "carrera": carrera,
                        "url_detalle": url,
                        "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "sedes": sedes,
                        "descripcion": descripcion,
                        "malla_url": malla_url,
                        "malla_curricular": malla_curricular
                    })
                    print(f"[{idx}/{len(urls)}] INACAP: {carrera} ({len(sedes)} sedes, {len(malla_curricular)} semestres)")

                except (TimeoutException, WebDriverException) as e:
                    print(f"[INACAP] Error en página: {url} -> {e}")
                    continue
                except Exception as e:
                    print(f"Error procesando {url}: {e}")

                if idx % 20 == 0 and idx < len(urls):
                    print(f"-> [INACAP] Liberando memoria RAM...")
                    driver.quit()
                    time.sleep(2)
                    driver = crear_driver()
        finally:
            driver.quit()