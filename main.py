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
        print("[S3] S3_BUCKET_NAME no configurado. Omitiendo subida a S3.")
        return False
    try:
        # En EC2 con LabRole o credenciales IAM, boto3 se autentica de forma transparente
        s3 = boto3.client("s3", region_name=AWS_REGION)
        key = f"raw/academic_offer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(datos, ensure_ascii=False, indent=2),
            ContentType="application/json; charset=utf-8"
        )
        print(f"[✓ S3] Respaldo guardado en: s3://{BUCKET_NAME}/{key}")
        return True
    except Exception as e:
        print(f"[✗ S3] Error al guardar en S3: {e}")
        return False

def guardar_en_rds(datos):
    if not DB_HOST or not DB_PASSWORD:
        print("[RDS] Error: Variables de base de datos no configuradas.")
        return False
    conn = None
    cur = None
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
        
        cur.execute("""
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
        """)

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
        print(f"[✓ RDS] Se actualizaron {len(filas)} registros en PostgreSQL.")
        return True
    except Exception as e:
        if conn is not None:
            conn.rollback()
        print(f"[✗ RDS] Error al insertar en PostgreSQL: {e}")
        return False
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

def ejecutar_pipeline():
    print(f"=== INICIO DEL PIPELINE ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
    todos_los_datos = []
    
    # 1. Duoc UC
    driver_links = crear_driver()
    try:
        duoc = DuocScraper()
        duoc.recolectar_enlaces(driver_links)
    finally:
        driver_links.quit()
    duoc.extraer_detalles()
    todos_los_datos.extend(duoc.datos_carreras)

    # 2. INACAP
    driver_links = crear_driver()
    try:
        inacap = InacapScraper()
        inacap.recolectar_enlaces(driver_links)
    finally:
        driver_links.quit()
    inacap.extraer_detalles()
    todos_los_datos.extend(inacap.datos_carreras)

    # 3. Almacenar resultados en la nube
    if todos_los_datos:
        print(f"\n[+] Total de carreras obtenidas: {len(todos_los_datos)}")
        s3_ok = guardar_en_s3(todos_los_datos)
        rds_ok = guardar_en_rds(todos_los_datos)
        if s3_ok and rds_ok:
            print("=== PIPELINE COMPLETADO EXITOSAMENTE ===")
        else:
            print("=== PIPELINE COMPLETADO CON ERRORES DE ALMACENAMIENTO ===")
    else:
        print("[!] No se extrajeron datos.")

if __name__ == "__main__":
    ejecutar_pipeline()