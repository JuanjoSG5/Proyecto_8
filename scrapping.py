import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
import random

# Configuración inicial - Modifica estas variables para cambiar el sitio a rastrear
INITIAL_URL = "https://www.eldiario.es/"
MAX_DEPTH = 2
# El nombre del archivo donde se guardará el progreso (se añade el dominio para tener un archivo por sitio)
PROGRESS_FILENAME = None  # Se generará automáticamente basado en el dominio

def setup_filenames():
    """Configura los nombres de archivos basados en el dominio actual"""
    global PROGRESS_FILENAME
    
    base_domain = urlparse(INITIAL_URL).netloc
    domain_slug = base_domain.replace('.', '_')
    
    PROGRESS_FILENAME = f"progress_{domain_slug}.json"
    return base_domain

def is_valid_url(url, base_domain):
    # Comprobar si la URL pertenece al mismo dominio y si es un enlace válido
    parsed_url = urlparse(url)
    return bool(parsed_url.netloc) and parsed_url.netloc == base_domain and parsed_url.scheme in ['http', 'https']

def save_progress(visited, links_jina, processed_links):
    """Guardar el progreso actual para poder retomarlo"""
    progress = {
        "visited": list(visited),
        "links_jina": list(links_jina),
        "processed_links": list(processed_links),
        "initial_url": INITIAL_URL,
        "max_depth": MAX_DEPTH
    }
    with open(PROGRESS_FILENAME, "w") as f:
        json.dump(progress, f)

def load_progress():
    """Cargar progreso guardado si existe"""
    if os.path.exists(PROGRESS_FILENAME):
        with open(PROGRESS_FILENAME, "r") as f:
            progress = json.load(f)
        
        # Verificar si es el mismo sitio y la misma configuración
        if progress.get("initial_url") == INITIAL_URL and progress.get("max_depth", MAX_DEPTH) == MAX_DEPTH:
            return set(progress["visited"]), set(progress["links_jina"]), set(progress["processed_links"])
        else:
            print(f"La configuración ha cambiado. Iniciando nuevo rastreo para {INITIAL_URL}")
    
    return set(), set(), set()

def scrape_url(url, depth, max_depth, base_domain, visited, links_jina, processed_links):
    if depth > max_depth:
        return
    
    try:
        # Si ya procesamos este URL, no hacemos nada
        if url in processed_links:
            return
            
        print(f"Procesando nivel {depth}: {url}")
        
        # Añadir retraso aleatorio para evitar ser bloqueado
        time.sleep(random.uniform(1, 3))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        # Marcar URL como procesado
        processed_links.add(url)
        save_progress(visited, links_jina, processed_links)
        
        for link in links:
            full_link = urljoin(url, link['href'])
            if full_link not in visited and is_valid_url(full_link, base_domain):
                visited.add(full_link)
                jina_link = "https://r.jina.ai/" + full_link
                links_jina.add(jina_link)
                print(f"Nivel {depth}: {full_link}")
                
                # Guardar progreso periódicamente
                if len(visited) % 10 == 0:
                    save_progress(visited, links_jina, processed_links)
                    
                scrape_url(full_link, depth + 1, max_depth, base_domain, visited, links_jina, processed_links)
                
    except requests.RequestException as e:
        print(f"Error al acceder a {url}: {e}")
        # En caso de error 429 (Too Many Requests), esperamos más tiempo
        if hasattr(e, 'response') and e.response and e.response.status_code == 429:
            wait_time = 60  # Esperar 1 minuto
            print(f"Recibido error 429. Esperando {wait_time} segundos antes de continuar...")
            time.sleep(wait_time)
        # Para otros errores, esperamos menos
        else:
            time.sleep(5)

def get_responses_dir():
    """Obtener el directorio para guardar las respuestas"""
    responses_dir = f"responses"
    
    if not os.path.exists(responses_dir):
        os.makedirs(responses_dir)
        
    return responses_dir

def get_links_file():
    """Obtener el nombre del archivo para guardar los links basado en el dominio"""
    base_domain = urlparse(INITIAL_URL).netloc
    domain_slug = base_domain.replace('.', '_')
    return f"linksJina_{domain_slug}.txt"

def download_responses(links_jina, processed_responses):
    """Descargar las respuestas de los enlaces Jina"""
    responses_dir = get_responses_dir()
    links_file = get_links_file()
    
    # Guardar links_jina en un archivo txt si no existe
    if not os.path.exists(links_file):
        with open(links_file, "w") as file:
            for link in links_jina:
                file.write(f"{link}\n")
    
    total = len(links_jina)
    for i, link in enumerate(links_jina):
        # Si ya procesamos este link, saltamos
        if link in processed_responses:
            continue
            
        filename = f"{responses_dir}/response{i}.md"
        
        # Si el archivo ya existe, marcamos como procesado y continuamos
        if os.path.exists(filename):
            processed_responses.add(link)
            continue
            
        try:
            print(f"Descargando {i+1}/{total}: {link}")
            
            # Añadir retraso para evitar ser bloqueado
            time.sleep(random.uniform(2, 5))
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }
            
            response = requests.get(link, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Guardar respuesta en un archivo
            with open(filename, "w", encoding="utf-8") as file:
                file.write(response.text)
                
            # Marcar como procesado
            processed_responses.add(link)
            
            # Guardar progreso periódicamente
            processed_responses_file = f"processed_responses_{urlparse(INITIAL_URL).netloc.replace('.', '_')}.json"
            if (i + 1) % 5 == 0:
                with open(processed_responses_file, "w") as f:
                    json.dump(list(processed_responses), f)
                    
        except requests.RequestException as e:
            print(f"Error al descargar {link}: {e}")
            # En caso de error 429, esperamos más tiempo
            if hasattr(e, 'response') and e.response and e.response.status_code == 429:
                wait_time = 120  # Esperar 2 minutos
                print(f"Recibido error 429. Esperando {wait_time} segundos antes de continuar...")
                time.sleep(wait_time)
            else:
                time.sleep(10)

def load_processed_responses():
    """Cargar las respuestas ya procesadas"""
    processed_responses_file = f"processed_responses_{urlparse(INITIAL_URL).netloc.replace('.', '_')}.json"
    if os.path.exists(processed_responses_file):
        with open(processed_responses_file, "r") as f:
            return set(json.load(f))
    return set()

def main():
    # Configurar nombres de archivos basados en dominio
    base_domain = setup_filenames()
    
    # Cargar progreso si existe
    visited, links_jina, processed_links = load_progress()
    processed_responses = load_processed_responses()
    
    # Si no hay progreso, comenzamos desde cero
    if not visited:
        print(f"Iniciando nuevo rastreo desde {INITIAL_URL}")
        scrape_url(INITIAL_URL, 1, MAX_DEPTH, base_domain, visited, links_jina, processed_links)
    else:
        print(f"Continuando rastreo desde donde se quedó. URLs visitadas: {len(visited)}")
        
        # Obtener URLs pendientes de procesar
        pending_urls = [url for url in visited if url not in processed_links]
        
        if pending_urls:
            # Continuamos con el scraping de URLs pendientes
            for url in pending_urls:
                # Determinar el nivel actual basado en la estructura de la URL
                path_parts = urlparse(url).path.strip('/').split('/')
                current_depth = min(len(path_parts) + 1, MAX_DEPTH)
                
                scrape_url(url, current_depth, MAX_DEPTH, base_domain, visited, links_jina, processed_links)

    # Imprimir total de links
    print(f"Total de links: {len(visited)}")
    print(f"Total de links Jina: {len(links_jina)}")
    
    # Descargar respuestas
    print("Iniciando descarga de respuestas...")
    download_responses(links_jina, processed_responses)
    
    print("Proceso completado exitosamente")

if __name__ == "__main__":
    main()