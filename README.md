# MiAyudante 🎓

Plataforma web integral orientada a la centralización, estructuración y consulta de oferta académica de educación superior técnico-profesional en Chile (INACAP y Duoc UC). El sistema consolida mallas curriculares, sedes, modalidades y aranceles mediante pipelines de web scraping automatizados, integrando herramientas de orientación vocacional asistida y consulta inteligente.

---

## 📌 Características Principales

* **Extracción Automatizada (Web Scraping):** Motores con Selenium para recolección concurrente de planes de estudio, mallas digitales y sedes de Duoc UC e INACAP.
* **Normalización de Datos Académicos:** Consolidación de catálogos formativos heterogéneos bajo esquemas estandarizados en formato JSON / Relacional.
* **Orientación Vocacional Integrada:** Módulo de diagnóstico vocacional basado en la metodología Ikigai para emparejamiento con perfiles de egreso.
* **Asistente Inteligente (RAG):** Motor de búsqueda semántica y recuperación contextual de carreras sobre bases de conocimiento institucionales.
* **Despliegue Cloud:** Infraestructura orientada a producción sobre Amazon Web Services (EC2, RDS PostgreSQL, S3).

---

## 🛠️ Stack Tecnológico

| Componente | Tecnologías |
| :--- | :--- |
| **Backend** | Python 3.10+, Django, Django REST Framework |
| **Scraping & Automatización** | Selenium WebDriver, Chromium / Google Chrome Headless |
| **Base de Datos** | PostgreSQL |
| **Almacenamiento & Cloud** | AWS (EC2, RDS, S3) |
| **IA & NLP** | RAG (Retrieval-Augmented Generation), LangChain / Embeddings |

---

## 📂 Estructura del Repositorio

```text
miayudante/
├── scrapers/
│   ├── base.py              # Clase base y configuración de WebDriver
│   ├── inacap_scraper.py    # Pipeline de extracción INACAP
│   ├── duoc_scraper.py      # Pipeline de extracción Duoc UC
│   └── run_scrapers.py      # Orquestador general de recolección
├── backend/
│   ├── manage.py
│   ├── core/                # Configuración global del proyecto Django
│   └── academic/            # App para gestión de carreras, sedes y mallas
├── data/
│   └── carreras_completas.json  # Dataset estructurado extraído
├── requirements.txt         # Dependencias del entorno Python
└── README.md