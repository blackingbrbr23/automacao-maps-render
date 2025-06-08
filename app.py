from flask import Flask, request, render_template_string, flash
import os
import time
import logging
import requests
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Configuração de logging
tlogging = logging.getLogger(__name__)
tlogging.setLevel(logging.INFO)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'changeme')

# Diretório para salvar resultados
data_dir = os.path.join(os.getcwd(), 'data')
os.makedirs(data_dir, exist_ok=True)

# Template HTML
TEMPLATE = '''
<!doctype html>
<title>Pesquisa Google Meu Negócio</title>
<h1>Pesquisa no Google Meu Negócio</h1>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul style="color:red;">
    {% for msg in messages %}<li>{{ msg }}</li>{% endfor %}
    </ul>
  {% endif %}
{% endwith %}
<form method="post">
  <label for="keywords">Palavras-chave (uma por linha):</label><br>
  <textarea name="keywords" rows="5" cols="40">{{ request.form.keywords or '' }}</textarea><br>
  <button type="submit">Pesquisar</button>
</form>
{% if results %}
  <h2>Resultados Encontrados</h2>
  <ul>
  {% for url in results %}
    <li><a href="{{ url }}" target="_blank">{{ url }}</a></li>
  {% endfor %}
  </ul>
{% endif %}
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        raw = request.form.get('keywords', '').strip()
        if not raw:
            flash('Informe pelo menos uma palavra-chave.')
            return render_template_string(TEMPLATE, results=None)
        keywords = [k.strip() for k in raw.splitlines() if k.strip()]
        try:
            results = run_search(keywords)
        except Exception as e:
            tlogging.error(f"Erro na busca: {e}")
            flash('Erro ao executar pesquisa. Verifique os logs.')
    return render_template_string(TEMPLATE, results=results)

def run_search(keywords):
    """
    Executa busca headless no Google Maps para cada palavra-chave e retorna lista de perfis.
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    driver.get('https://www.google.com/maps?hl=pt-BR')
    time.sleep(3)

    collected = set()
    for kw in keywords:
        tlogging.info(f'Buscando: {kw}')
        campo = driver.find_element(By.ID, 'searchboxinput')
        campo.clear()
        campo.send_keys(kw)
        campo.send_keys(Keys.ENTER)
        time.sleep(5)

        prev = 0
        for _ in range(15):
            perfis = driver.find_elements(By.CSS_SELECTOR, 'a.hfpxzc')
            curr = len(perfis)
            if curr == prev:
                break
            prev = curr
            driver.execute_script('arguments[0].scrollIntoView();', perfis[-1])
            time.sleep(2)

        for p in perfis:
            href = p.get_attribute('href')
            if href:
                collected.add(href)

    driver.quit()

    # Grava em arquivo
    out_file = os.path.join(data_dir, 'links.txt')
    with open(out_file, 'w', encoding='utf-8') as f:
        for url in sorted(collected):
            f.write(url + '\n')

    return sorted(collected)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
