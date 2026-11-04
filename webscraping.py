import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://scrapingsandbox.com"
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
}
TAMANHO_PAGINA = 24
MAX_PAGINAS = 100
TENTATIVAS = 3
TIMEOUT = 20

_cache = None
_trava = threading.Lock()


def limpar_preco(valor):
    if valor is None or valor == '':
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    limpo = re.sub(r'[^\d.]', '', str(valor).replace(',', ''))
    try:
        return float(limpo) if limpo else None
    except ValueError:
        return None


def limpar_avaliacao(valor):
    if valor is None or valor == '':
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        achado = re.search(r'\d+(?:\.\d+)?', str(valor))
        return float(achado.group()) if achado else None


def buscar_produto(sessao, base_url, produto_id):
    url = f"{base_url}/product/{produto_id}"
    ultimo_erro = None

    for tentativa in range(TENTATIVAS):
        try:
            resposta = sessao.get(url, headers=HEADERS, timeout=TIMEOUT)

            if resposta.status_code == 404:
                return None
            if resposta.status_code == 429 or resposta.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resposta.status_code}")
            resposta.raise_for_status()

            soup = BeautifulSoup(resposta.text, 'html.parser')
            bloco = (soup.find('pre')
                     or soup.find('script', type='application/json')
                     or soup.find('code'))
            if bloco is None:
                return None
            dados = json.loads(bloco.get_text())

            return {
                'nome': dados['title'],
                'preco': limpar_preco(dados.get('price')),
                'categoria': dados.get('category'),
                'avaliacao': limpar_avaliacao(dados.get('rating')),
                'link': url,
            }
        except (requests.RequestException, ValueError, KeyError) as erro:
            ultimo_erro = erro
            if tentativa < TENTATIVAS - 1:
                time.sleep(2 ** tentativa)

    raise RuntimeError(f"Falha ao coletar o produto {produto_id}: {ultimo_erro}")


def coletar_pagina(sessao, base_url, numero_pagina):
    inicio = (numero_pagina - 1) * TAMANHO_PAGINA + 1
    ids = range(inicio, inicio + TAMANHO_PAGINA)
    produtos, falhas, inexistentes = [], [], 0

    def tarefa(produto_id):
        return buscar_produto(sessao, base_url, produto_id)

    with ThreadPoolExecutor(max_workers=5) as executor:
        resultados = list(executor.map(lambda i: _seguro(tarefa, i), ids))

    for produto_id, resultado in zip(ids, resultados):
        if isinstance(resultado, Exception):
            falhas.append(produto_id)
        elif resultado is None:
            inexistentes += 1
        else:
            produtos.append(resultado)

    existentes = len(ids) - inexistentes
    return produtos, existentes, falhas


def _seguro(funcao, argumento):
    try:
        return funcao(argumento)
    except RuntimeError as erro:
        return erro


def coletar_produtos(base_url=BASE_URL, usar_cache=True):
    global _cache
    with _trava:
        if usar_cache and _cache is not None:
            return _cache.copy()

        todos, falhas_totais = [], []
        with requests.Session() as sessao:
            for pagina in range(1, MAX_PAGINAS + 1):
                produtos, existentes, falhas = coletar_pagina(sessao, base_url, pagina)
                print(f"Página {pagina}: {len(produtos)} produtos coletados")
                todos.extend(produtos)
                falhas_totais.extend(falhas)

                if existentes == 0 and not falhas:
                    break

            for rodada in range(1, 4):
                if not falhas_totais:
                    break
                time.sleep(3 * rodada)
                ainda_falhando = []
                for produto_id in falhas_totais:
                    try:
                        produto = buscar_produto(sessao, base_url, produto_id)
                        if produto is not None:
                            todos.append(produto)
                    except RuntimeError:
                        ainda_falhando.append(produto_id)
                falhas_totais = ainda_falhando

        if falhas_totais:
            print(f"AVISO: {len(falhas_totais)} produto(s) não foram coletados "
                  f"(ids {falhas_totais[:10]}). Os cálculos podem estar incompletos.")

        if not todos:
            raise RuntimeError("Nenhum produto foi coletado do Scraping Sandbox.")

        df = pd.DataFrame(todos).drop_duplicates(subset='link').reset_index(drop=True)
        print(f"Coleta concluída: {len(df)} produtos em {pagina} página(s).")

        if not falhas_totais:
            _cache = df
        return df.copy()