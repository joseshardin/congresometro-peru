import sqlite_utils
import json

def crear_base_de_datos():
    """
    Esta función toma el JSON que ya tenemos y lo mete en SQLite.
    Solo necesitamos correr esto una vez (o cuando queramos actualizar).
    """
    
    # Abrimos (o creamos si no existe) el archivo de base de datos
    # sqlite_utils.Database() hace todo el trabajo pesado por nosotros
    db = sqlite_utils.Database("congresometro.db")
    
    # Leemos el JSON que ya tenemos
    print("Leyendo congresistas.json...")
    with open("congresistas.json", encoding="utf-8") as f:
        congresistas = json.load(f)
    
    print(f"Cargando {len(congresistas)} congresistas en la base de datos...")
    
    # Si la tabla ya existe, la borramos para empezar limpio
    # Útil cuando corremos el script varias veces
    if "congresistas" in db.table_names():
        db["congresistas"].drop()
        print("Tabla anterior eliminada.")
    
    # Insertamos todos los congresistas de una sola vez
    # sqlite_utils detecta automáticamente las columnas desde el diccionario
    db["congresistas"].insert_all(
        congresistas,
        alter=True  # Si hay columnas nuevas, las agrega automáticamente
    )
    
    print(f"✅ Insertados {db['congresistas'].count} registros")
    
    # Creamos índices para que las búsquedas sean rápidas
    # Un índice es como el índice de un libro: te lleva directo a lo que buscas
    # Sin índice, SQLite lee fila por fila (lento con millones de registros)
    db["congresistas"].create_index(["region"], if_not_exists=True)
    db["congresistas"].create_index(["grupo_parlamentario"], if_not_exists=True)
    
    print("Índices creados.")
    
    # Mostramos las columnas que se crearon
    print(f"\nColumnas en la tabla:")
    for col in db["congresistas"].columns:
        print(f"  - {col.name} ({col.type})")
    
    return db


def consultas_de_ejemplo(db):
    """
    Hacemos algunas consultas para verificar que todo está bien.
    SQL es el lenguaje para hablar con bases de datos.
    SELECT = dame estos campos
    FROM   = de esta tabla  
    WHERE  = que cumplan esta condición
    ORDER  = ordenados por
    LIMIT  = solo los primeros N
    """
    
    print("\n--- CONSULTAS DE EJEMPLO ---\n")
    
    # Consulta 1: Total de congresistas
    # execute() envía SQL directo a la base de datos
    resultado = db.execute("SELECT COUNT(*) FROM congresistas").fetchone()
    print(f"Total congresistas: {resultado[0]}")
    
    # Consulta 2: Top 5 con más votos
    print("\nTop 5 congresistas con más votos:")
    filas = db.execute("""
        SELECT nombre, region, grupo_parlamentario, CAST(votos AS INTEGER) as votos_num
        FROM congresistas
        WHERE votos IS NOT NULL AND votos != ''
        ORDER BY votos_num DESC
        LIMIT 5
    """).fetchall()
    
    for fila in filas:
        print(f"  {fila[3]:>8,} votos - {fila[0]} ({fila[2][:20]})")
    
    # Consulta 3: Congresistas por región
    print("\nRegiones con más congresistas:")
    filas = db.execute("""
        SELECT region, COUNT(*) as total
        FROM congresistas
        GROUP BY region
        ORDER BY total DESC
        LIMIT 8
    """).fetchall()
    
    for fila in filas:
        print(f"  {fila[1]:>3} - {fila[0]}")
    
    # Consulta 4: Buscar por partido
    print("\nCongresistas de Renovación Popular:")
    filas = db.execute("""
        SELECT nombre, region
        FROM congresistas
        WHERE grupo_parlamentario = 'RENOVACIÓN POPULAR'
        ORDER BY nombre
    """).fetchall()
    
    for fila in filas:
        print(f"  {fila[0]} ({fila[1]})")
        
def cargar_proyectos(db):
    """
    Toma el archivo proyectos.json y lo mete en SQLite.
    Crea una tabla separada relacionada con la de congresistas.
    """
    
    import json
    import os
    
    if not os.path.exists("proyectos.json"):
        print("No existe proyectos.json todavía")
        return
    
    with open("proyectos.json", encoding="utf-8") as f:
        proyectos = json.load(f)
    
    print(f"Cargando {len(proyectos)} proyectos...")
    
    # Eliminamos tabla anterior si existe
    if "proyectos" in db.table_names():
        db["proyectos"].drop()
    
    # Insertamos todos
    db["proyectos"].insert_all(proyectos, alter=True)
    
    # Índices para búsquedas rápidas
    db["proyectos"].create_index(["congresista_nombre"], if_not_exists=True)
    db["proyectos"].create_index(["estado"], if_not_exists=True)
    db["proyectos"].create_index(["fecha"], if_not_exists=True)
    
    print(f"✅ {db['proyectos'].count} proyectos en la base de datos")
    
    # Consultas de ejemplo
    print("\n--- ESTADÍSTICAS ---")
    
    # Proyectos por estado
    print("\nProyectos por estado:")
    filas = db.execute("""
        SELECT estado, COUNT(*) as total
        FROM proyectos
        GROUP BY estado
        ORDER BY total DESC
    """).fetchall()
    for f in filas:
        print(f"  {f[1]:>5} - {f[0]}")
    
    # Congresistas más activos
    print("\nCongresistas con más proyectos:")
    filas = db.execute("""
        SELECT congresista_nombre, COUNT(*) as total
        FROM proyectos
        GROUP BY congresista_nombre
        ORDER BY total DESC
        LIMIT 5
    """).fetchall()
    for f in filas:
        print(f"  {f[1]:>4} - {f[0]}")        


if __name__ == "__main__":
    db = crear_base_de_datos()
    consultas_de_ejemplo(db)
    cargar_proyectos(db)