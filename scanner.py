# -------------------------------------------------------------------
# scanner.py
# -------------------------------------------------------------------
# Coleta links no Google Maps a partir de uma lista de palavras‐chave
# em modo headless, e grava em dados/links.txt.
# -------------------------------------------------------------------

import os
import sys
import time
import logging
import re
import requests
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# -------------------------------------------------------------
# Configuração de logging
# -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------
# URL do painel remoto (vai buscar em variável de ambiente)
# -------------------------------------------------------------
PAINEL_URL = os.environ.get("PAINEL_URL", "https://painel-api-k2v2.onrender.com/command")

def get_mac():
    """
    Retorna o endereço MAC principal do sistema:
    Windows: via 'getmac'
    Linux/Mac: via 'ifconfig'
    Se falhar, retorna None e loga o erro.
    """
    try:
        if sys.platform.startswith("win"):
            import subprocess
            output = subprocess.check_output("getmac", encoding="cp1252", errors="ignore")
            macs = re.findall(r"([0-9A-Fa-f]{2}[-:]){5}[0-9A-Fa-f]{2}", output)
            return macs[0].replace("-", ":").lower() if macs else None
        else:
            import subprocess
            output = subprocess.check_output("ifconfig", encoding="utf-8", errors="ignore")
            macs = re.findall(r"([0-9A-Fa-f]{2}[:]){5}[0-9A-Fa-f]{2}", output)
            return macs[0].lower() if macs else None
    except Exception as e:
        logger.error(f"Erro ao obter MAC: {e}")
        return None

def verificar_liberacao(mac, tentativas=3, intervalo=2) -> bool:
    """
    Tenta até `tentativas` vezes verificar no painel se o cliente está ativo.
    Se JSON retornar {"ativo": true}, devolve True, caso contrário False.
    """
    for tentativa in range(1, tentativas + 1):
        try:
            ip = requests.get("https://api.ipify.org", timeout=5).text
            r = requests.get(PAINEL_URL, params={"mac": mac, "public_ip": ip}, timeout=10)
            r.raise_for_status()
            return r.json().get("ativo", False)
        except Exception as e:
            logger.error(f"Tentativa {tentativa}/{tentativas} falhou: {e}")
            if tentativa < tentativas:
                time.sleep(intervalo)
    return False

def load_saved_links(links_file):
    if not os.path.exists(links_file):
        return set()
    with open(links_file, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def save_new_links(new_links, links_file):
    existing = load_saved_links(links_file)
    to_add = new_links - existing
    if not to_add:
        logger.warning("Nenhum link novo para adicionar.")
        return
    with open(links_file, 'a', encoding='utf-8') as f:
        for link in sorted(to_add):
            f.write(link + '\n')
    logger.info(f"Adicionados {len(to_add)} novos links. Total: {len(existing | new_links)}")

def coletar_links_por_busca(busca, driver, links_file):
    """
    Dado um termo `busca`, faz scroll na página de resultados do Google Maps e
    coleta todos os links de perfil (CSS selector "a.hfpxzc"), gravando-os.
    """
    logger.info(f"🔍 Buscando: {busca}")
    campo = driver.find_element(By.ID, 'searchboxinput')
    campo.clear()
    campo.send_keys(busca)
    campo.send_keys(Keys.ENTER)
    time.sleep(5)

    prev = 0
    for i in range(20):
        perfis = driver.find_elements(By.CSS_SELECTOR, 'a.hfpxzc')
        curr = len(perfis)
        logger.info(f"  ▶️ Scroll {i+1}: {curr} perfis carregados")
        if curr == prev:
            break
        prev = curr
        driver.execute_script("arguments[0].scrollIntoView();", perfis[-1])
        time.sleep(2)

    links = {p.get_attribute('href') for p in perfis if p.get_attribute('href')}
    save_new_links(links, links_file)

def run_scanner(keywords, dados_dir):
    """
    Ponto de entrada para disparar a coleta de links:
      - Verifica liberação no painel remoto
      - Cria/usa o arquivo dados/links.txt
      - Inicia Selenium headless, navega no Maps, coleta para cada keyword
    """
    mac = get_mac()
    if not mac:
        logger.error("Não foi possível obter o endereço MAC. Abortando.")
        return

    logger.info("→ Verificando liberação junto ao painel remoto…")
    if not verificar_liberacao(mac):
        logger.error("Cliente BLOQUEADO. Abortando.")
        return

    LINKS_FILE = os.path.join(dados_dir, "links.txt")
    logger.info(f"⚙️ Iniciando coleta para {len(keywords)} palavras-chave.")

    # Configura Selenium Firefox em modo headless
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)

    # Navega no Google Maps
    driver.get("https://www.google.com/maps/@-16.4932735,-39.3111171,12z?hl=pt-BR")
    time.sleep(5)

    for idx, chave in enumerate(keywords, 1):
        logger.info(f"=== EXECUTANDO {idx}/{len(keywords)}: '{chave}' ===")
        coletar_links_por_busca(chave, driver, LINKS_FILE)

    driver.quit()
    logger.info("🏁 Processo de coleta de links finalizado.")
