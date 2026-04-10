from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd

# Diccionario maestro: Aquí controlas todas las webs y sus etiquetas exactas
webs_a_scrapear = {
    "Peruautos": {
        "url": "https://www.peruautos.pe/auto/category/suv/",
        "clase_contenedor": "col-md-4", 
        "clase_titulo": "title",
        "clase_precio": "price",
        "clase_km": "mileage"
    },
    "NeoAuto": {
        "url": "https://neoauto.com/venta-de-autos--camionetas-suv",
        "clase_contenedor": "c-results-use__item",
        "clase_titulo": "c-results-use__title",
        "clase_precio": "c-results-use__price",
        "clase_km": "c-results-use__km"
    },
    "Autocosmos": {
        "url": "https://www.autocosmos.com.pe/auto/usado?tipo=suv",
        "clase_contenedor": "listing-card",
        "clase_titulo": "listing-card__title",
        "clase_precio": "listing-card__price",
        "clase_km": "listing-card__km"
    },
    "MercadoLibre": {
        "url": "https://listado.mercadolibre.com.pe/autos-camionetas-suv",
        "clase_contenedor": "ui-search-layout__item",
        "clase_titulo": "ui-search-item__title",
        "clase_precio": "price-tag-fraction",
        "clase_km": "ui-search-card-attributes__attribute"
    }
}

def extraer_texto(elemento, clase):
    """Función de apoyo para evitar errores si un dato no existe"""
    encontrado = elemento.find(class_=clase)
    return encontrado.get_text(strip=True) if encontrado else "No especificado"

def iniciar_scraping_masivo():
    # Aquí está la corrección: se añadieron los corchetes para crear una lista vacía
    todas_las_gangas = []

    with sync_playwright() as p:
        # Iniciamos el navegador. headless=False para que veas cómo trabaja
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for portal, config in webs_a_scrapear.items():
            print(f"Scrapeando {portal}...")
            try:
                page.goto(config["url"], timeout=60000)
                # Esperamos a que el sitio cargue su contenido dinámico
                page.wait_for_timeout(5000) 
                
                # Desplazarse un poco hacia abajo para cargar imágenes y precios (Lazy Load)
                page.evaluate("window.scrollBy(0, 1000)")
                page.wait_for_timeout(2000)

                html_content = page.content()
                soup = BeautifulSoup(html_content, 'html.parser')

                # Buscamos todos los contenedores de autos en esta web específica
                anuncios = soup.find_all(class_=config["clase_contenedor"])
                print(f"Se encontraron {len(anuncios)} anuncios en {portal}")

                for anuncio in anuncios:
                    titulo = extraer_texto(anuncio, config["clase_titulo"])
                    precio = extraer_texto(anuncio, config["clase_precio"])
                    km = extraer_texto(anuncio, config["clase_km"])
                    
                    # Solo guardamos si realmente encontró un título
                    if titulo!= "No especificado":
                        todas_las_gangas.append({
                            'Portal': portal,
                            'Modelo': titulo,
                            'Precio': precio,
                            'Kilometraje': km,
                            'Link Base': config["url"]
                        })
            
            except Exception as e:
                print(f"Error al scrapear {portal}: {e}")
                continue # Si una web falla (ej. bloquea el bot), pasa a la siguiente

        browser.close()

    # Guardamos el resultado consolidado
    if todas_las_gangas:
        df = pd.DataFrame(todas_las_gangas)
        df.to_csv('gangas_totales_peru.csv', index=False, encoding='utf-8')
        print(f"¡Éxito! Se consolidaron {len(todas_las_gangas)} autos en 'gangas_totales_peru.csv'.")
    else:
        print("No se extrajeron datos. Debes ajustar las clases CSS en el diccionario 'webs_a_scrapear'.")

if __name__ == '__main__':
    iniciar_scraping_masivo()