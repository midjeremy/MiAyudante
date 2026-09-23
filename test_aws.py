import os
import json
from datetime import datetime
from dotenv import load_dotenv
import boto3
import psycopg2
from psycopg2.extras import execute_values, Json

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "miayudantedb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

datos_prueba = [
    {
        "institucion": "INACAP",
        "carrera": "Ingeniería en Informática (TEST)",
        "url_detalle": "https://portal.inacap.cl/carreras/test-informatica",
        "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sedes": ["Sede La Granja", "Sede Santiago Sur"],
        "descripcion": "Registro de prueba de conexión a AWS.",
        "malla_url": "https://portal.inacap.cl/malla-test",
        "malla_curricular": {"1er Semestre": ["Introducción a la Programación - INF101"]}
    }
]

def probar_s3():
    print("\n--- [1/2] Probando subida a AWS S3 ---")
    if not BUCKET_NAME:
        print("✗ Error: S3_BUCKET_NAME no definido.")
        return False
    try:
        # En EC2 con LabRole, boto3 detecta automáticamente el perfil IAM
        s3 = boto3.client("s3", region_name=AWS_REGION)
        test_key = f"raw/test_conexion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=test_key,
            Body=json.dumps(datos_prueba, ensure_ascii=False, indent=2),
            ContentType="application/json; charset=utf-8"
        )
        print(f"✓ Conexión exitosa con S3. Archivo: s3://{BUCKET_NAME}/{test_key}")
        return True
    except Exception as e:
        print(f"✗ Falló la conexión a S3: {e}")
        return False

def probar_rds():
    print("\n--- [2/2] Probando conexión a AWS RDS PostgreSQL ---")
    if not DB_HOST or not DB_PASSWORD:
        print("✗ Error: DB_HOST o DB_PASSWORD faltantes.")
        return False

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

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=8
        )
        cur = conn.cursor()
        cur.execute(sql_create)
        
        fila = [(
            datos_prueba[0]["url_detalle"],
            datos_prueba[0]["institucion"],
            datos_prueba[0]["carrera"],
            datos_prueba[0]["descripcion"],
            Json(datos_prueba[0]["sedes"]),
            datos_prueba[0]["malla_url"],
            Json(datos_prueba[0]["malla_curricular"]),
            datos_prueba[0]["fecha_extraccion"]
        )]
        execute_values(cur, sql_upsert, fila)
        conn.commit()

        cur.execute("SELECT carrera, sedes FROM academic_offer WHERE url_detalle = %s;", (datos_prueba[0]["url_detalle"],))
        res = cur.fetchone()
        cur.close()
        conn.close()

        print(f"✓ Conexión exitosa con RDS PostgreSQL. Registro verificado: {res[0]}")
        return True
    except Exception as e:
        print(f"✗ Falló conexión a RDS: {e}")
        return False

if __name__ == "__main__":
    s3_ok = probar_s3()
    rds_ok = probar_rds()
    if s3_ok and rds_ok:
        print("\n🎉 ¡TODOS LOS SERVICIOS FUNCIONAN CORRECTAMENTE EN AWS!")