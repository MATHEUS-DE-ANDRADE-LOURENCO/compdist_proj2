"""stress_test.py

Script simples para gerar requisições concorrentes ao endpoint
`POST /agendamentos` e demonstrar comportamento de exclusão mútua.

Este script cria várias threads (uma por requisição) que tentam inserir
agendamentos para o mesmo `horario`/`telescopio`. O objetivo é observar
quantas requisições resultam em 201 (criado) versus 409 (conflito/locked).

Uso:
    python3 stress_test.py --workers 10 --requests 100

Nota: o parâmetro `--workers` atualmente não controla um pool real — o
script cria uma thread por requisição para maximizar concorrência. Para
cenários mais sofisticados, use `concurrent.futures` ou bibliotecas de
stress específicas.
"""

import argparse
import threading
import requests
import time
import random


def make_request(url, payload, results, idx):
    """Realiza uma única requisição POST e grava o resultado em `results[idx]`.

    Armazena uma tupla `(status_code, response_text)` ou `(0, error)` em caso
    de exceção. Timeout curto para evitar threads presas.
    """
    try:
        r = requests.post(url, json=payload, timeout=10)
        results[idx] = (r.status_code, r.text)
    except Exception as e:
        results[idx] = (0, str(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=5)
    parser.add_argument('--requests', type=int, default=20)
    parser.add_argument('--url', default='http://localhost:5000/agendamentos')
    args = parser.parse_args()

    # Escolhemos um horário fixo para concentrar todas as requisições no mesmo recurso
    horario = '2026-01-01T00:00:00Z'
    payloads = []
    for i in range(args.requests):
        payloads.append({'cientista_id': random.randint(1,50), 'telescopio': 'Hubble-Acad', 'horario_inicio_utc': horario})

    results = [None] * args.requests
    threads = []
    for i in range(args.requests):
        # Criamos uma thread por requisição para gerar alta concorrência
        t = threading.Thread(target=make_request, args=(args.url, payloads[i], results, i))
        threads.append(t)

    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    end = time.time()

    # Estatísticas simples: quantas requisições resultaram em 201/409/outros
    successes = sum(1 for r in results if r and r[0] == 201)
    conflicts = sum(1 for r in results if r and r[0] == 409)
    others = len([r for r in results if r and r[0] not in (201,409)])

    print(f'Total {len(results)} requests in {end-start:.2f}s. 201: {successes}, 409: {conflicts}, other: {others}')
    for idx, r in enumerate(results):
        print(idx, r)


if __name__ == '__main__':
    main()
