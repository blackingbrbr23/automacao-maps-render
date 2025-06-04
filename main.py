# -------------------------------------------------------------------
# main.py
# -------------------------------------------------------------------
# EntryPoint: faz loop contínuo rodando scanner e filterer a cada 1 hora
# -------------------------------------------------------------------

import os
import time
import logging
from scanner import run_scanner
from filterer import run_filter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Se você montou um Persistent Volume em /mnt/dados, defina DATA_DIR para "/mnt/dados"
    # Caso contrário, usaremos uma pasta "dados/" relativa
    DADOS_DIR = os.environ.get("DATA_DIR", None) or os.path.join(os.path.dirname(__file__), "dados")
    os.makedirs(DADOS_DIR, exist_ok=True)

    # Lista de palavras-chave: pode vir de variável de ambiente KEYWORDS ou estar fixa aqui
    raw = os.environ.get("KEYWORDS", "")
    if raw:
        keywords = raw.split(";")
    else:
        # Caso queira deixar aqui mesmo, use ponto e vírgula para separar
        keywords = [
            "restaurante delivery Salvador",
            "hotel praia Grande"
        ]

    while True:
        logger.info("===== CICLO: coleta de links =====")
        run_scanner(keywords, DADOS_DIR)

        logger.info("===== CICLO: filtragem de perfis =====")
        run_filter(DADOS_DIR)

        # Grava último horário de término em um arquivo “status.txt”
        try:
            status_path = os.path.join(DADOS_DIR, "status.txt")
            with open(status_path, "a") as f:
                f.write(f"Ciclo finalizado em {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception as e:
            logger.error(f"Não foi possível gravar status: {e}")

        logger.info("===== CICLO concluído. Aguardando 1 hora =====")
        time.sleep(3600)
