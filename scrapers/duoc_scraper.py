import re
import time
import requests
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scrapers.driver import crear_driver

class DuocScraper:
    def __init__(self):
        self.institucion = "DUOC UC"
        self.url_base = "https://www.duoc.cl/oferta-academica/carreras/"
        self.urls_a_visitar = set()
        self.datos_carreras = []

    def _cargar_todas_las_tarjetas(self, driver):
        while True:
            try:
                boton_ver_mas = driver.find_elements(By.CSS_SELECTOR, "button.bc-btn-ver-mas")
                if not boton_ver_mas or not boton_ver_mas[0].is_displayed():
                    break
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

            # 1. Pestaña Profesionales
            self._cargar_todas_las_tarjetas(driver)
            cards = driver.find_elements(By.CSS_SELECTOR, ".bc-card h3 a, a.bc-ver-carrera")
            for elem in cards:
                href = elem.get_attribute("href")
                if href and "/carreras/" in href:
                    clean_url = href.split("?")[0].rstrip("/")
                    if not clean_url.endswith("/carreras") and not clean_url.endswith("duoc.cl"):
                        self.urls_a_visitar.add(clean_url)

            # 2. Pestaña Técnicas
            pestana_tecnicas = driver.find_elements(By.CSS_SELECTOR, "button.bc-tab[data-tipo='Técnica']")
            if pestana_tecnicas:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pestana_tecnicas[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", pestana_tecnicas[0])
                time.sleep(3)

                self._cargar_todas_las_tarjetas(driver)
                cards_tec = driver.find_elements(By.CSS_SELECTOR, ".bc-card h3 a, a.bc-ver-carrera")
                for elem in cards_tec:
                    href = elem.get_attribute("href")
                    if href and "/carreras/" in href:
                        clean_url = href.split("?")[0].rstrip("/")
                        if not clean_url.endswith("/carreras") and not clean_url.endswith("duoc.cl"):
                            self.urls_a_visitar.add(clean_url)

            print(f"[{self.institucion}] Total de carreras encontradas: {len(self.urls_a_visitar)}")
        except Exception as e:
            print(f"[{self.institucion}] Error recolectando catálogo: {e}")

    def _parsear_html_malla_duoc(self, html_str):
        """Parsea el HTML de una malla interactiva de Duoc UC y extrae semestres."""
        div_tags = re.findall(
            r'(<div[^>]+class="[^"]*(?<![\w-])mc-subject(?![\w-])[^"]*"[^>]*>)(.*?)(?=<div[^>]+class="[^"]*(?<![\w-])mc-subject(?![\w-])|\Z)',
            html_str,
            re.DOTALL
        )
        malla_dict = {}
        for open_tag, inner in div_tags:
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', open_tag))
            name_match = re.search(r'<span class="mc-name">(.*?)</span>', inner, re.DOTALL)
            name = name_match.group(1).strip() if name_match else ""
            if not name and 'aria-label' in attrs:
                name = attrs['aria-label'].split('—')[0].split('(')[0].strip()

            sem = attrs.get('data-sem', 'General').strip()
            code = attrs.get('data-code', '').strip()

            if not sem:
                sem = "General"

            if sem not in malla_dict:
                malla_dict[sem] = []

            if code:
                item_str = f"{name} - {code}"
            else:
                if attrs.get('data-elective') == '1' or 'Cupo electivo' in inner or 'mc-elective' in open_tag:
                    item_str = f"{name} - Cupo electivo"
                else:
                    item_str = name

            if item_str and item_str not in malla_dict[sem]:
                malla_dict[sem].append(item_str)

        return malla_dict

    def _obtener_mallas_duoc(self, mallas_info):
        """Descarga y parsea cada archivo html de las mallas digitales."""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        # Caso 1: Carrera con 1 sola malla
        if len(mallas_info) == 1:
            url = mallas_info[0]["url"]
            try:
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    return url, self._parsear_html_malla_duoc(res.text)
            except Exception:
                pass
            return url, {}

        # Caso 2: Carrera con múltiples menciones (ej: Ingeniería en Informática)
        urls_list = [m["url"] for m in mallas_info]
        mallas_agrupadas = {}
        for item in mallas_info:
            mencion_key = item["mencion_id"] or "mencion"
            try:
                res = requests.get(item["url"], headers=headers, timeout=10)
                if res.status_code == 200:
                    mallas_agrupadas[mencion_key] = self._parsear_html_malla_duoc(res.text)
            except Exception:
                mallas_agrupadas[mencion_key] = {}

        return urls_list, mallas_agrupadas

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
                            descripcion = " ".join([p.text.strip() for p in textos if p.text.strip()])
                        else:
                            desc_meta = driver.find_element(By.CSS_SELECTOR, "meta[name='description']")
                            descripcion = desc_meta.get_attribute("content") or "Sin descripción disponible"
                    except:
                        descripcion = "Sin descripción disponible"

                    # 3. Sedes (Lista limpia de strings con mayúsculas iniciales)
                    sedes = []
                    try:
                        bloques_sedes = driver.find_elements(By.CSS_SELECTOR, "#sedes-y-aranceles .cont-blanco.sedes-aranceles h4")
                        for h4 in bloques_sedes:
                            nombre = h4.text.replace("SEDE", "").strip().title()
                            if nombre and nombre not in sedes:
                                sedes.append(nombre)
                    except:
                        pass

                    # 4. Extracción de URLs de mallas interactivas (.dmc-root)
                    mallas_info = []
                    try:
                        elementos_dmc = driver.find_elements(By.CSS_SELECTOR, ".dmc-root[data-dmc-src]")
                        for el in elementos_dmc:
                            m_id = el.get_attribute("data-dmc-id") or ""
                            m_src = el.get_attribute("data-dmc-src") or ""
                            if m_src and m_src not in [x["url"] for x in mallas_info]:
                                mallas_info.append({"mencion_id": m_id, "url": m_src})

                        if not mallas_info:
                            botones_malla = driver.find_elements(By.CSS_SELECTOR, "#malla-de-la-carrera .dmc-abrir-malla a")
                            for btn in botones_malla:
                                href = btn.get_attribute("href")
                                if href:
                                    m_id = href.split("#dmc-malla-")[-1] if "#dmc-malla-" in href else "general"
                                    mallas_info.append({"mencion_id": m_id, "url": href})
                    except Exception as e:
                        print(f"Error localizando enlaces de malla en {url}: {e}")

                    # 5. Obtener estructura de ramos por semestre
                    if mallas_info:
                        malla_url, malla_curricular = self._obtener_mallas_duoc(mallas_info)
                    else:
                        malla_url = url
                        malla_curricular = {}

                    self.datos_carreras.append({
                        "institucion": self.institucion,
                        "carrera": carrera,
                        "url_detalle": url,
                        "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "sedes": sedes if sedes else ["Consultar sedes en portal Duoc"],
                        "descripcion": descripcion,
                        "malla_url": malla_url,
                        "malla_curricular": malla_curricular
                    })
                    print(f"[{idx}/{len(urls)}] Duoc UC: {carrera}")

                except Exception as e:
                    print(f"Error procesando {url}: {e}")

                if idx % 20 == 0 and idx < len(urls):
                    print(f"-> [Duoc UC] Liberando memoria RAM...")
                    driver.quit()
                    time.sleep(2)
                    driver = crear_driver()
        finally:
            driver.quit()