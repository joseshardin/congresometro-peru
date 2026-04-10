import requests
import json
import time
import re
from playwright.sync_api import sync_playwright

# ─────────────────────────────────────────
# FASE 1: Obtener el codigo de cada congresista
# ─────────────────────────────────────────

def obtener_todos_los_codigos(congresistas):
    """
    Usa Playwright para visitar la página de proyectos de cada congresista
    e interceptar la llamada a la API que contiene el 'codigo'.
    """
    
    resultados = []
    sin_codigo = []
    
    with sync_playwright() as p:
        # headless=True → navegador invisible, más rápido
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        total = len(congresistas)
        
        for i, congresista in enumerate(congresistas):
            nombre = congresista["nombre"]
            web = congresista.get("web_personal", "")
            
            if not web:
                sin_codigo.append(nombre)
                continue
            
            url = web + "laborlegislativa/proyectos-ley/"
            codigo_capturado = {}
            
            # Función que se ejecuta cada vez que el browser hace una request
            def capturar(request):
                if "spley-portal-service/proyecto-ley" in request.url:
                    match = re.search(r'codigo=([^&]+)', request.url)
                    if match:
                        codigo_capturado['valor'] = match.group(1)
            
            # Registramos el listener ANTES de navegar
            page.on("request", capturar)
            
            print(f"[{i+1:3d}/{total}] {nombre[:45]}", end="", flush=True)
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                # Esperamos a que el JS haga la llamada a la API
                page.wait_for_timeout(4000)
                
                if 'valor' in codigo_capturado:
                    congresista['codigo_api'] = codigo_capturado['valor']
                    resultados.append(congresista)
                    print(f" ✓ {codigo_capturado['valor']}")
                else:
                    sin_codigo.append(nombre)
                    print(" ✗ sin codigo")
                    
            except Exception as e:
                sin_codigo.append(nombre)
                print(f" ⚠ error: {str(e)[:40]}")
            
            # Removemos el listener para el siguiente congresista
            page.remove_listener("request", capturar)
            
            # Pausa entre páginas
            time.sleep(1)
        
        browser.close()
    
    print(f"\nCon código: {len(resultados)} | Sin código: {len(sin_codigo)}")
    return resultados


# ─────────────────────────────────────────
# FASE 2: Bajar proyectos via API directa
# ─────────────────────────────────────────

def obtener_proyectos(nombre, codigo):
    """
    Llama directamente a la API del congreso con el codigo del congresista.
    Devuelve lista de proyectos de ley.
    """
    
    url = f"https://api.congreso.gob.pe/spley-portal-service/proyecto-ley/2021?codigo={codigo}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0",
        "Accept": "application/json"
    }
    
    try:
        respuesta = requests.get(url, headers=headers, timeout=15)
        
        if respuesta.status_code != 200:
            print(f"  ✗ Error HTTP {respuesta.status_code}")
            return []
        
        data = respuesta.json()
        
        if data.get("code") != 200:
            return []
        
        proyectos = []
        for p in data.get("data", []):
            proyecto = {
                "congresista_nombre": nombre,
                # Número del proyecto (ej: 14091)
                "numero": p.get("pleyNum"),
                # Código completo (ej: "14091/2025-CR")
                "codigo_proyecto": p.get("proyectoLey"),
                # Fecha de presentación
                "fecha": p.get("fecPresentacion"),
                # Estado actual (EN COMISIÓN, APROBADO, ARCHIVADO, etc.)
                "estado": p.get("desEstado"),
                # Título completo
                "titulo": p.get("titulo"),
                # Legislatura (ej: "2025 - 2026")
                "legislatura": p.get("desPerLeg"),
            }
            proyectos.append(proyecto)
        
        return proyectos
        
    except Exception as e:
        print(f"  ⚠ Error: {e}")
        return []


# ─────────────────────────────────────────
# PROGRAMA PRINCIPAL
# ─────────────────────────────────────────

def main():
    
    # Cargamos la lista de congresistas
    with open("congresistas.json", encoding="utf-8") as f:
        congresistas = json.load(f)
    
    print(f"Total congresistas: {len(congresistas)}")
    print("=" * 60)
    
    # ── FASE 1 ──
    print("\nFASE 1: Capturando códigos de API...\n")
    
    # Para probar, usamos solo los primeros 5
    # Cuando funcione bien, cambia a: congresistas_muestra = congresistas
    congresistas_muestra = congresistas
    
    con_codigos = obtener_todos_los_codigos(congresistas_muestra)
    
    # Guardamos progreso por si algo falla después
    with open("congresistas_con_codigo.json", "w", encoding="utf-8") as f:
        json.dump(con_codigos, f, ensure_ascii=False, indent=2)
    
    print(f"\nCódigos guardados en congresistas_con_codigo.json")
    
    # ── FASE 2 ──
    print("\nFASE 2: Descargando proyectos de ley...\n")
    
    todos_proyectos = []
    
    for congresista in con_codigos:
        nombre = congresista["nombre"]
        codigo = congresista["codigo_api"]
        
        print(f"  {nombre[:45]}", end="", flush=True)
        
        proyectos = obtener_proyectos(nombre, codigo)
        todos_proyectos.extend(proyectos)
        
        print(f" → {len(proyectos)} proyectos")
        
        # Pausa entre llamadas a la API
        time.sleep(0.5)
    
    # Guardamos todos los proyectos
    with open("proyectos.json", "w", encoding="utf-8") as f:
        json.dump(todos_proyectos, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Total proyectos: {len(todos_proyectos)}")
    print("Guardados en proyectos.json")
    
    # Mostramos muestra
    print("\nEjemplos:")
    for p in todos_proyectos[:3]:
        print(f"  [{p['estado']}] {p['titulo'][:70]}")


if __name__ == "__main__":
    main()