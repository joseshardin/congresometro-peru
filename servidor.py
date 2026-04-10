from flask import Flask, jsonify, send_file
from flask_cors import CORS
import sqlite_utils

app = Flask(__name__)
CORS(app)

def get_db():
    return sqlite_utils.Database("congresometro.db")

@app.route("/")
def index():
    return send_file("dashboard.html")

@app.route("/api/resumen")
def resumen():
    db = get_db()
    total_congresistas = db.execute("SELECT COUNT(*) FROM congresistas").fetchone()[0]
    total_proyectos = db.execute("SELECT COUNT(*) FROM proyectos").fetchone()[0]
    aprobados = db.execute("SELECT COUNT(*) FROM proyectos WHERE estado = 'APROBADO'").fetchone()[0]
    publicados = db.execute("SELECT COUNT(*) FROM proyectos WHERE estado = 'Publicada en el Diario Oficial El Peruano'").fetchone()[0]
    return jsonify({
        "total_congresistas": total_congresistas,
        "total_proyectos": total_proyectos,
        "aprobados": aprobados,
        "publicados": publicados
    })

@app.route("/api/congresistas")
def congresistas():
    db = get_db()
    filas = db.execute("""
        SELECT 
            c.nombre, c.region, c.grupo_parlamentario, c.votos, c.condicion, c.foto_url,
            COUNT(p.numero) as total_proyectos,
            SUM(CASE WHEN p.estado = 'APROBADO' THEN 1 ELSE 0 END) as aprobados,
            SUM(CASE WHEN p.estado = 'Publicada en el Diario Oficial El Peruano' THEN 1 ELSE 0 END) as publicados
        FROM congresistas c
        LEFT JOIN proyectos p ON c.nombre = p.congresista_nombre
        GROUP BY c.nombre
        ORDER BY total_proyectos DESC
    """).fetchall()
    return jsonify([{
        "nombre": f[0], "region": f[1], "partido": f[2], "votos": f[3],
        "condicion": f[4], "foto_url": f[5], "total_proyectos": f[6],
        "aprobados": f[7] or 0, "publicados": f[8] or 0
    } for f in filas])

@app.route("/api/partidos")
def partidos():
    db = get_db()
    filas = db.execute("""
        SELECT c.grupo_parlamentario, COUNT(DISTINCT c.nombre) as miembros,
               COUNT(p.numero) as total_proyectos,
               SUM(CASE WHEN p.estado = 'APROBADO' THEN 1 ELSE 0 END) as aprobados
        FROM congresistas c
        LEFT JOIN proyectos p ON c.nombre = p.congresista_nombre
        GROUP BY c.grupo_parlamentario
        ORDER BY total_proyectos DESC
    """).fetchall()
    return jsonify([{
        "partido": f[0], "miembros": f[1], "total_proyectos": f[2], "aprobados": f[3] or 0
    } for f in filas])

@app.route("/api/estados")
def estados():
    db = get_db()
    filas = db.execute("""
        SELECT estado, COUNT(*) as total FROM proyectos GROUP BY estado ORDER BY total DESC
    """).fetchall()
    return jsonify([{"estado": f[0], "total": f[1]} for f in filas])

@app.route("/api/congresista/<path:nombre>")
def congresista_detalle(nombre):
    db = get_db()
    fila = db.execute("""
        SELECT nombre, region, grupo_parlamentario, votos,
               condicion, foto_url, web_personal, email, periodo_inicio, periodo_fin
        FROM congresistas WHERE nombre = ?
    """, [nombre]).fetchone()

    if not fila:
        return jsonify({"error": "No encontrado", "buscado": nombre}), 404

    congresista = {
        "nombre": fila[0], "region": fila[1], "partido": fila[2],
        "votos": fila[3], "condicion": fila[4], "foto_url": fila[5],
        "web_personal": fila[6], "email": fila[7],
        "periodo_inicio": fila[8], "periodo_fin": fila[9]
    }

    proyectos = db.execute("""
        SELECT numero, codigo_proyecto, fecha, estado, titulo, legislatura
        FROM proyectos WHERE congresista_nombre = ?
        ORDER BY fecha DESC
    """, [nombre]).fetchall()

    congresista["proyectos"] = [{
        "numero": p[0], "codigo": p[1], "fecha": p[2],
        "estado": p[3], "titulo": p[4], "legislatura": p[5]
    } for p in proyectos]

    congresista["stats"] = {
        "total": len(congresista["proyectos"]),
        "aprobados": sum(1 for p in congresista["proyectos"] if p["estado"] == "APROBADO"),
        "publicados": sum(1 for p in congresista["proyectos"] if p["estado"] == "Publicada en el Diario Oficial El Peruano"),
        "en_comision": sum(1 for p in congresista["proyectos"] if p["estado"] == "EN COMISIÓN"),
        "archivados": sum(1 for p in congresista["proyectos"] if "Archivo" in (p["estado"] or ""))
    }

    return jsonify(congresista)
  
@app.route("/api/rankings")
def rankings():
    db = get_db()
    
    filas = db.execute("""
        SELECT 
            c.nombre,
            c.region,
            c.grupo_parlamentario,
            c.foto_url,
            c.votos,
            COUNT(p.numero) as total_proyectos,
            SUM(CASE WHEN p.estado = 'APROBADO' THEN 1 ELSE 0 END) as aprobados,
            SUM(CASE WHEN p.estado = 'Publicada en el Diario Oficial El Peruano' 
                THEN 1 ELSE 0 END) as publicados,
            SUM(CASE WHEN p.estado IN ('Al Archivo','DECRETO DE ARCHIVO') 
                THEN 1 ELSE 0 END) as archivados,
            SUM(CASE WHEN p.estado = 'Retirado por su Autor' 
                THEN 1 ELSE 0 END) as retirados
        FROM congresistas c
        LEFT JOIN proyectos p ON c.nombre = p.congresista_nombre
        GROUP BY c.nombre
        HAVING total_proyectos > 0
    """).fetchall()
    
    datos = []
    for f in filas:
        total = f[5] or 1
        aprobados = f[6] or 0
        archivados = f[8] or 0
        retirados = f[9] or 0
        
        datos.append({
            "nombre": f[0],
            "region": f[1],
            "partido": f[2],
            "foto_url": f[3],
            "votos": f[4],
            "total_proyectos": f[5],
            "aprobados": aprobados,
            "publicados": f[7] or 0,
            "archivados": archivados,
            "retirados": retirados,
            # % de proyectos que terminaron archivados o retirados
            "pct_inutil": round((archivados + retirados) / total * 100, 1),
            # % de proyectos aprobados
            "pct_aprobado": round(aprobados / total * 100, 2),
        })
    
    return jsonify({
        # VERGÜENZA
        "menos_activos": sorted(datos, key=lambda x: x["total_proyectos"])[:10],
        "mas_archivados": sorted(datos, key=lambda x: x["pct_inutil"], reverse=True)[:10],
        "cero_aprobados": [d for d in datos if d["aprobados"] == 0],
        "peor_ratio": sorted(
            [d for d in datos if d["total_proyectos"] >= 50],
            key=lambda x: x["pct_aprobado"]
        )[:10],
        # HONOR
        "mas_activos": sorted(datos, key=lambda x: x["total_proyectos"], reverse=True)[:10],
        "mas_aprobados": sorted(datos, key=lambda x: x["aprobados"], reverse=True)[:10],
        "mejor_ratio": sorted(
            [d for d in datos if d["total_proyectos"] >= 50],
            key=lambda x: x["pct_aprobado"],
            reverse=True
        )[:10],
    })  

@app.route("/api/sin-actividad")
def sin_actividad():
    db = get_db()  # ← faltaba esta línea
    filas = db.execute("""
        SELECT c.nombre, c.region, c.grupo_parlamentario, c.foto_url, c.votos
        FROM congresistas c
        LEFT JOIN proyectos p ON c.nombre = p.congresista_nombre
        WHERE p.congresista_nombre IS NULL
        ORDER BY c.nombre
    """).fetchall()
    
    return jsonify([{
        "nombre": f[0],
        "region": f[1],
        "partido": f[2],
        "foto_url": f[3],
        "votos": f[4],
        "total_proyectos": 0,
        "aprobados": 0
    } for f in filas])


if __name__ == "__main__":
    print("Servidor corriendo en http://localhost:5000")
    app.run(debug=True, port=5000)