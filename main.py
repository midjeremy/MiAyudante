import os
import json
from datetime import datetime
from dotenv import load_dotenv
import boto3
import psycopg2
from psycopg2.extras import execute_values, Json

from scrapers.driver import crear_driver
from scrapers.duoc_scraper import DuocScraper
from scrapers.inacap_scraper import InacapScraper

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "miayudantedb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

def guardar_en_s3(datos):
    if not BUCKET_NAME:
        print("[S3] S3_BUCKET_NAME no configurado. Se omite respaldo en S3.")
        return
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"raw/academic_offer_{timestamp}.json"
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(datos, ensure_ascii=False, indent=2),
            ContentType="application/json; charset=utf-8"
        )
        print(f"[S3] Respaldo guardado exitosamente en s3://{BUCKET_NAME}/{key}")
    except Exception as e:
        print(f"[S3] Error al guardar en S3: {e}")

def guardar_en_rds(datos):
    if not DB_HOST or not DB_PASSWORD:
        print("[RDS] Variables DB_HOST o DB_PASSWORD faltantes.")
        return
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=10
        )
        cur = conn.cursor()
        
        sql_create = """
        CREATE TABLE IF NOT EXISTS academic_offer (
            url_detalle VARCHAR(500) PRIMARY KEY,
            institucion VARCHAR(100) NOT NULL,
            carrera VARCHAR(250) NOT NULL,
            descripcion TEXT,
            sedes JSONB,
            malla_url TEXT,
            malla_curricular JSONB,
            fecha_extraccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(sql_create)

        sql_upsert = """
        INSERT INTO academic_offer (url_detalle, institucion, carrera, descripcion, sedes, malla_url, malla_curricular, fecha_extraccion)
        VALUES %s
        ON CONFLICT (url_detalle) DO UPDATE SET
            institucion = EXCLUDED.institucion,
            carrera = EXCLUDED.carrera,
            descripcion = EXCLUDED.descripcion,
            sedes = EXCLUDED.sedes,
            malla_url = EXCLUDED.malla_url,
            malla_curricular = EXCLUDED.malla_curricular,
            fecha_extraccion = CURRENT_TIMESTAMP;
        """

        filas = [
            (
                d["url_detalle"],
                d["institucion"],
                d["carrera"],
                d["descripcion"],
                Json(d["sedes"]),
                d["malla_url"],
                Json(d["malla_curricular"]),
                d["fecha_extraccion"]
            )
            for d in datos
        ]

        execute_values(cur, sql_upsert, filas)
        conn.commit()
        cur.close()
        conn.close()
        print(f"[RDS] Se insertaron/actualizaron {len(filas)} registros en PostgreSQL.")
    except Exception as e:
        print(f"[RDS] Error al persistir en base de datos: {e}")

def ejecutar_pipeline():
    print("=== INICIANDO PIPELINE DE EXTRACCIÓN Y CARGA ===")
    driver = crear_driver()
    todos_los_datos = []
    
    try:
        # 1. Duoc UC
        duoc = DuocScraper(driver)
        duoc.recolectar_enlaces()
        duoc.extraer_detalles()
        todos_los_datos.extend(duoc.datos_carreras)

        # 2. INACAP
        inacap = InacapScraper(driver)
        inacap.recolectar_enlaces()
        inacap.extraer_detalles()
        todos_los_datos.extend(inacap.datos_carreras)

    finally:
        driver.quit()
        print("[+] Navegador cerrado.")

    if todos_los_datos:
        print(f"\n[+] Total registros procesados: {len(todos_los_datos)}")
        guardar_en_s3(todos_los_datos)
        guardar_en_rds(todos_los_datos)
        print("=== PROCESO FINALIZADO CON ÉXITO ===")
    else:
        print("[!] No se obtuvieron datos para persistir.")

if __name__ == "__main__":
    ejecutar_pipeline()