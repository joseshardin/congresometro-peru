import requests
from bs4 import BeautifulSoup
import json
import time  # Para hacer pausas entre requests

def extraer_perfil(url_perfil, nombre):
    """
    Esta función extrae los datos del perfil de UN congresista.
    Recibe la URL del perfil y el nombre como referencia.
    Devuelve un diccionario con los datos extra.
    """
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0"
    }
    
    try:
        # try/except: si algo falla, no rompe todo el programa
        # Es como un "intenta esto, y si falla haz aquello"
        respuesta = requests.get(url_perfil, headers=headers, timeout=10)
        
        if respuesta.status_code != 200:
            return {}
        
        soup = BeautifulSoup(respuesta.text, "html.parser")
        
        datos = {}
        
        # Extraer votación obtenida
        # Buscamos el elemento con class="votacion" y dentro el span con class="value"
        elem_votacion = soup.find("p", class_="votacion")
        if elem_votacion:
            valor = elem_votacion.find("span", class_="value")
            if valor:
                # Limpiamos comas y convertimos a número
                datos["votos"] = valor.text.strip().replace(",", "")
        
        # Extraer fecha inicio y fin de funciones
        periodos = soup.find_all("span", class_="periododatos")
        if len(periodos) >= 2:
            inicio = periodos[0].find("span", class_="value")
            fin = periodos[1].find("span", class_="value")
            if inicio:
                datos["periodo_inicio"] = inicio.text.strip()
            if fin:
                datos["periodo_fin"] = fin.text.strip()
        
        # Extraer condición (en ejercicio, suspendido, etc.)
        elem_condicion = soup.find("p", class_="condicion")
        if elem_condicion:
            valor = elem_condicion.find("span", class_="value")
            if valor:
                datos["condicion"] = valor.text.strip()
        
        # Extraer URL de foto
        foto = soup.find("div", class_="foto")
        if foto:
            img = foto.find("img")
            if img and img.get("src"):
                datos["foto_url"] = "https://www3.congreso.gob.pe" + img["src"]
        
        # Extraer URL de web personal del congresista
        elem_web = soup.find("p", class_="web")
        if elem_web:
            link = elem_web.find("a")
            if link and link.get("href"):
                datos["web_personal"] = link["href"]
        
        return datos
    
    except Exception as e:
        # Si algo falla (timeout, error de red, etc.) simplemente devolvemos vacío
        # y continuamos con el siguiente congresista
        print(f"  ⚠ Error en {nombre}: {e}")
        return {}


def obtener_congresistas():
    
    url = "https://www3.congreso.gob.pe/pagina/distrito-electoral"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0"
    }
    
    print("Conectando a congreso.gob.pe...")
    respuesta = requests.get(url, headers=headers, timeout=15)
    
    if respuesta.status_code != 200:
        print(f"Error: {respuesta.status_code}")
        return
    
    soup = BeautifulSoup(respuesta.text, "html.parser")
    congresistas = []
    region_actual = "Sin región"
    filas = soup.find_all("tr")
    
    for fila in filas:
        encabezado = fila.find("h2")
        if encabezado:
            region_actual = encabezado.text.strip()
            continue
        
        celdas = fila.find_all("td")
        if len(celdas) != 5:
            continue
        
        link_nombre = celdas[2].find("a")
        if not link_nombre:
            continue
        
        nombre = link_nombre.text.strip()
        grupo = celdas[3].text.strip()
        link_email = celdas[4].find("a")
        email = link_email.text.strip() if link_email else ""
        href = link_nombre.get("href", "")
        url_perfil = f"https://www3.congreso.gob.pe{href}" if href else ""
        
        congresista = {
            "nombre": nombre,
            "region": region_actual,
            "grupo_parlamentario": grupo,
            "email": email,
            "url_perfil": url_perfil
        }
        
        congresistas.append(congresista)
    
    print(f"Lista base: {len(congresistas)} congresistas encontrados")
    print("Ahora entrando a cada perfil para obtener más datos...")
    print("(Esto toma ~3 minutos. Pausa 1 seg entre cada uno para no saturar el servidor)\n")
    
    # Ahora entramos al perfil de CADA congresista
    for i, congresista in enumerate(congresistas):
        
        nombre = congresista["nombre"]
        url_perfil = congresista["url_perfil"]
        
        # Mostramos progreso: número actual / total
        print(f"[{i+1:3d}/130] {nombre[:40]}", end="", flush=True)
        
        if url_perfil:
            datos_extra = extraer_perfil(url_perfil, nombre)
            # Combinamos los datos base con los datos extra del perfil
            # update() agrega todas las claves del diccionario datos_extra al congresista
            congresista.update(datos_extra)
            print(f" ✓ votos: {datos_extra.get('votos', 'n/d')}")
        else:
            print(" ✗ sin URL")
        
        # Pausa de 1 segundo entre cada request
        # Importante: no queremos sobrecargar el servidor del congreso
        # y también evitamos que nos bloqueen por hacer demasiadas requests rápidas
        time.sleep(1)
    
    # Guardamos todo
    with open("congresistas.json", "w", encoding="utf-8") as archivo:
        json.dump(congresistas, archivo, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Listo. Datos guardados en congresistas.json")
    print(f"Total: {len(congresistas)} congresistas con datos completos")


if __name__ == "__main__":
    obtener_congresistas()