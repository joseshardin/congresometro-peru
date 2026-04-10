from playwright.sync_api import sync_playwright
import json, re

def encontrar_codigos():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Capturamos la URL de la API cuando se llama
        codigos_encontrados = {}
        
        def capturar_api(request):
            url = request.url
            if "spley-portal-service/proyecto-ley" in url:
                # Extraemos el codigo de la URL
                match = re.search(r'codigo=([^&]+)', url)
                if match:
                    codigo = match.group(1)
                    codigos_encontrados['codigo'] = codigo
                    print(f"  ✓ codigo capturado: {codigo}")
        
        page.on("request", capturar_api)
        
        # Probamos con 5 congresistas diferentes
        webs = [
            ("Infantes Castañeda, Mery Eliana", "https://www3.congreso.gob.pe/congresistas2021/MeryInfantes/laborlegislativa/proyectos-ley/"),
            ("Montalvo Cubas, Segundo Toribio", "https://www3.congreso.gob.pe/congresistas2021/SegundoMontalvo/laborlegislativa/proyectos-ley/"),
            ("Camones Soriano, Lady Mercedes", "https://www3.congreso.gob.pe/congresistas2021/LadyCamones/laborlegislativa/proyectos-ley/"),
        ]
        
        resultados = []
        
        for nombre, url in webs:
            codigos_encontrados.clear()
            print(f"\n{nombre}")
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(5000)
                
                if 'codigo' in codigos_encontrados:
                    resultados.append({
                        "nombre": nombre,
                        "web": url,
                        "codigo": codigos_encontrados['codigo']
                    })
                else:
                    print("  ✗ no se encontró codigo")
            except Exception as e:
                print(f"  Error: {e}")
        
        browser.close()
        
        print("\n--- RESULTADOS ---")
        for r in resultados:
            print(f"  {r['nombre']}: {r['codigo']}")
        
        with open("codigos.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    encontrar_codigos()