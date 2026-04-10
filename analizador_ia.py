import google.generativeai as genai
import sqlite_utils
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")
db = sqlite_utils.Database("congresometro.db")

if "analisis_ia" not in db.table_names():
    db["analisis_ia"].create({
        "proyecto_codigo": str,
        "congresista_nombre": str,
        "titulo": str,
        "estado": str,
        "categoria": str,
        "beneficiario": str,
        "impacto_pueblo": int,
        "etiquetas": str,
        "resumen_ia": str,
        "bandera_roja": int,
        "analizado_en": str,
    }, pk="proyecto_codigo")
    print("Tabla analisis_ia creada")

ya_analizados = set(row["proyecto_codigo"] for row in db["analisis_ia"].rows)

proyectos = db.execute("""
    SELECT codigo_proyecto, congresista_nombre, titulo, estado
    FROM proyectos
    WHERE estado = 'APROBADO'
    AND codigo_proyecto IS NOT NULL
    ORDER BY fecha DESC
""").fetchall()

pendientes = [p for p in proyectos if p[0] not in ya_analizados]

print(f"Total aprobados: {len(proyectos)} | Ya analizados: {len(ya_analizados)} | Pendientes: {len(pendientes)}")

if not pendientes:
    print("Todo analizado!")
    exit()

PROMPT = """Eres un analista político experto en el Congreso del Perú.
Analiza este proyecto de ley aprobado SOLO basándote en su título.

Título: "{titulo}"
Congresista: {congresista}

Responde SOLO con JSON válido, sin backticks ni texto extra:
{{"categoria": "beneficioso|neutral|sospechoso|bandera_roja|interesante", "beneficiario": "quién se beneficia (max 60 chars)", "impacto_pueblo": <1-10>, "etiquetas": ["tag1","tag2","tag3"], "resumen_ia": "qué hace esta ley en una oración (max 120 chars)", "bandera_roja": <true|false>}}

Criterios:
- beneficioso: salud, educación, derechos ciudadanos, infraestructura pública
- neutral: cambios administrativos, plazos, tecnicismos
- sospechoso: favorece sectores privados, posible conflicto de interés
- bandera_roja: exoneraciones fiscales, beneficia grupos de poder, contradice interés público
- interesante: anticorrupción, transparencia, reformas importantes"""

def analizar(codigo, congresista, titulo, estado, intento=1):
    try:
        response = model.generate_content(
            PROMPT.format(titulo=titulo, congresista=congresista)
        )
        texto = response.text.strip()
        inicio = texto.find("{")
        fin = texto.rfind("}") + 1
        if inicio != -1 and fin > inicio:
            texto = texto[inicio:fin]
        data = json.loads(texto)
        return {
            "proyecto_codigo": codigo,
            "congresista_nombre": congresista,
            "titulo": titulo,
            "estado": estado,
            "categoria": data.get("categoria", "neutral"),
            "beneficiario": data.get("beneficiario", ""),
            "impacto_pueblo": int(data.get("impacto_pueblo", 5)),
            "etiquetas": json.dumps(data.get("etiquetas", []), ensure_ascii=False),
            "resumen_ia": data.get("resumen_ia", ""),
            "bandera_roja": 1 if data.get("bandera_roja") else 0,
            "analizado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except json.JSONDecodeError:
        print(f"  JSON invalido, saltando")
        return None
    except Exception as e:
        msg = str(e)
        if "429" in msg or "quota" in msg.lower():
            espera = 15 * intento
            print(f"  Rate limit, esperando {espera}s...")
            time.sleep(espera)
            if intento < 4:
                return analizar(codigo, congresista, titulo, estado, intento + 1)
        print(f"  Error: {msg[:100]}")
        return None

guardados = 0
errores = 0

print(f"\nIniciando analisis de {len(pendientes)} proyectos APROBADOS con Gemini Flash...\n")

for i, (codigo, congresista, titulo, estado) in enumerate(pendientes):
    print(f"[{i+1}/{len(pendientes)}] {titulo[:70]}...")
    resultado = analizar(codigo, congresista, titulo, estado)
    if resultado:
        db["analisis_ia"].upsert(resultado, pk="proyecto_codigo")
        guardados += 1
        bandera = " BANDERA ROJA" if resultado["bandera_roja"] else ""
        print(f"  [{resultado['categoria'].upper()}] impacto:{resultado['impacto_pueblo']}/10{bandera}")
        print(f"  {resultado['resumen_ia'][:90]}")
    else:
        errores += 1
    time.sleep(5)

print(f"\nFIN: {guardados} guardados, {errores} errores")
print("\nRESUMEN:")
cats = db.execute("SELECT categoria, COUNT(*), ROUND(AVG(impacto_pueblo),1) FROM analisis_ia GROUP BY categoria ORDER BY 2 DESC").fetchall()
emojis = {"beneficioso":"🟢","neutral":"🟡","sospechoso":"🟠","bandera_roja":"🔴","interesante":"🔵"}
for cat, total, avg in cats:
    print(f"  {emojis.get(cat,'⚪')} {cat}: {total} proyectos (impacto promedio: {avg}/10)")

print("\nBANDERAS ROJAS:")
banderas = db.execute("""
    SELECT congresista_nombre, resumen_ia, impacto_pueblo
    FROM analisis_ia WHERE bandera_roja = 1
    ORDER BY impacto_pueblo ASC
""").fetchall()
for c, r, imp in banderas:
    print(f"  🚩 {c.split(',')[0]}: {r}")
