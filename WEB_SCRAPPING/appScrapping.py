import time
import json
from datetime import datetime
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class InacapScraper:
    def __init__(self):
        # Configuración de Chrome en modo invisible y resolución de escritorio
        opciones = webdriver.ChromeOptions()
        opciones.add_argument("--headless=new")
        opciones.add_argument("--disable-gpu")
        opciones.add_argument("--log-level=3")
        opciones.add_argument("--window-size=1920,1080") 
        
        self.driver = webdriver.Chrome(options=opciones)
        self.urls_a_visitar = []
        self.datos_carreras_completos = []
        self.url_base = "https://portal.inacap.cl/carreras/"

    # Recoleccion de enlaces de carreras
    def recolectar_enlaces(self):
        """Fase 1: Entra al portal principal y guarda las URLs de las carreras."""
        print("Iniciando Fase 1: Recolectando URLs de las carreras...")
        self.driver.get(self.url_base)

        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".border-bottom-radius-15"))
        )

        enlaces = self.driver.find_elements(By.CSS_SELECTOR, ".border-bottom-radius-15 a")

        for enlace in enlaces:
            texto = enlace.get_attribute("textContent")
            if texto:
                texto = texto.strip().lower()
                
            url = enlace.get_attribute("href")
            
            if texto and "ver carrera" in texto and url:
                if url not in self.urls_a_visitar:
                    self.urls_a_visitar.append(url)

        print(f"Se encontraron {len(self.urls_a_visitar)} carreras para analizar.\n")

    #Extraer detalles y malla digital
    def extraer_detalles(self):
        """Extrae los detalles, sedes, fecha y la malla digital agrupada por semestre."""
        print("Iniciando Fase 2: Extrayendo detalles y mallas digitales...")
        
        for url_carrera in self.urls_a_visitar:
            print(f"\nAnalizando: {url_carrera}")
            self.driver.get(url_carrera)
            
            try:
                # 1. Extraer título principal
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
                titulo = self.driver.find_element(By.TAG_NAME, "h1").text
                
                # 2. Extraer descripción
                try:
                    descripcion = self.driver.find_element(By.CSS_SELECTOR, ".interior-panel").text
                except:
                    descripcion = "Sin descripción disponible"

                # 3. Extraer Sedes donde se imparte
                sedes_impartidas = []
                try:
                    # Se usa get_attribute("textContent") para extraer el texto aunque el acordeón esté cerrado[cite: 3]
                    elementos_sedes = self.driver.find_elements(By.CSS_SELECTOR, ".sidebarCarrera__sedes .interiorCarrera-sede p")
                    for el in elementos_sedes:
                        texto_sede = el.get_attribute("textContent").strip()
                        if texto_sede:
                            sedes_impartidas.append(texto_sede)
                except Exception as e:
                    print(f"  [!] No se pudieron extraer las sedes: {e}")
                    
                # 4. Leer la malla digital. Se ignora deliberadamente el PDF:
                # sus columnas no representan de forma fiable el semestre.
                enlace_malla = None
                malla_curricular = {}
                malla_error = None
                try:
                    enlace_malla = self._obtener_enlace_malla()
                    malla_curricular = self._extraer_malla_curricular(enlace_malla)
                except Exception as e:
                    malla_error = str(e)
                    print(f"  [!] No se pudo extraer la malla digital: {e}")

                # 5. Obtener fecha actual del scraping
                fecha_extraccion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 6. Guardar todo el objeto de la carrera
                carrera = {
                    "carrera": titulo,
                    "url_detalle": url_carrera,
                    "fecha_extraccion": fecha_extraccion,
                    "sedes": sedes_impartidas,
                    "descripcion": descripcion,
                    "malla_url": enlace_malla,
                    "malla_curricular": malla_curricular
                }
                if malla_error:
                    carrera["malla_error"] = malla_error
                self.datos_carreras_completos.append(carrera)
                
                time.sleep(1) # Pausa de cortesía con el servidor
                
            except Exception as e:
                print(f"Error general al procesar {url_carrera}: {e}")
                continue

    # obtener enlace de la malla digital
    def _obtener_enlace_malla(self):
        """Obtiene el enlace de la malla digital desde la página de la carrera."""
        enlace = self.driver.find_element(
            By.CSS_SELECTOR,
            "a[href*='Inacap.Siga.MallaCurricular']"
        ).get_attribute("href")
        if not enlace:
            raise ValueError("La carrera no contiene un enlace a la malla digital")
        return urljoin(self.url_base, enlace)

    
    #extraer malla curricular
    def _extraer_malla_curricular(self, enlace_malla):
        """Agrupa las tarjetas de cada columna de la malla en su semestre."""
        self.driver.get(enlace_malla)
        
        # CAMBIO CLAVE: Esperar a que Angular renderice las tarjetas reales, no solo la tabla
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "td.tarjeta .font-asignatura"))
        )

        # Ahora sí capturamos la tabla sabiendo que está poblada
        tabla = self.driver.find_element(By.ID, "tblPrincipal")

        encabezados = tabla.find_elements(By.CSS_SELECTOR, ":scope > tbody > tr:first-child > td h4")
        if not encabezados:
            raise ValueError("La malla digital no contiene encabezados de semestre")

        malla = {encabezado.text.strip(): [] for encabezado in encabezados}
        columnas = list(malla)
        
        # Ignoramos la primera fila (encabezados)
        filas = tabla.find_elements(By.CSS_SELECTOR, ":scope > tbody > tr")[1:]

        for fila in filas:
            # Seleccionamos solo las celdas directas de la fila principal (colspan="2")
            celdas = fila.find_elements(By.CSS_SELECTOR, ":scope > td")
            
            for indice, celda in enumerate(celdas[:len(columnas)]):
                # Buscamos las tarjetas dentro de las tablas anidadas (tblData)
                tarjetas = celda.find_elements(By.CSS_SELECTOR, "td.tarjeta")
                
                for tarjeta in tarjetas:
                    asignatura = tarjeta.find_elements(By.CSS_SELECTOR, ".font-asignatura")
                    codigo = tarjeta.find_elements(By.CSS_SELECTOR, ".font-codigo")
                    
                    nombre = asignatura[0].text.strip() if asignatura else ""
                    identificador = codigo[0].text.strip() if codigo else ""
                    
                    # Esto filtra las celdas fantasma generadas por los ng-hide de Angular
                    if nombre and identificador:
                        malla[columnas[indice]].append(f"{nombre} - {identificador}")

        return malla

    # Guardar datos en JSON
    def guardar_datos(self, nombre_archivo="carreras_con_archivos.json"):
        """Exporta los datos recolectados a un archivo JSON."""
        with open(nombre_archivo, 'w', encoding='utf-8') as archivo_json:
            json.dump(self.datos_carreras_completos, archivo_json, ensure_ascii=False, indent=4)
        print(f"\n¡Proceso completado! JSON guardado en '{nombre_archivo}'.")

    # Cerrar navegador
    def cerrar_navegador(self):
        """Cierra la instancia de Chrome."""
        self.driver.quit()

    # Orquestador
    def ejecutar_scraping(self):
        """Método orquestador."""
        try:
            self.recolectar_enlaces()
            self.extraer_detalles()
        finally:
            self.cerrar_navegador()
            self.guardar_datos()

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    scraper = InacapScraper()
    scraper.ejecutar_scraping()