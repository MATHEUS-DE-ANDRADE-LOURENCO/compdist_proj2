# Relatório do projeto `compdist_proj2`

## Contexto

- Objetivo: sistema de agendamento distribuído para demonstrar controle de concorrência e coordenação de locks entre serviços que reservam recursos (telescópios).
- Estrutura principal do repositório:
  - `docker-compose.yml` — orquestra os serviços.
  - `servico-agendamento/` — serviço em Flask (Python), API REST para agendamentos, persistência em SQLite e logs/auditoria.
  - `servico-coordenador/` — serviço em Node.js (Express), implementa um coordenador de locks em memória.
  - `servico-agendamento/stress_test.py` — script para gerar carga concorrente contra `POST /agendamentos`.

---

## Arquitetura

- Dois serviços principais orquestrados por `docker-compose`:
  - `servico-coordenador` (Node/Express): coordena locks para recursos (recurso = `telescopio + horario`) com TTL em memória.
  - `servico-agendamento` (Flask/SQLAlchemy): API REST que valida solicitações, solicita locks ao coordenador, persiste agendamentos em SQLite e gera logs/auditoria.
- Comunicação entre serviços: via HTTP (o Flask chama `COORDINATOR_URL` para `/lock/acquire` e `/lock/release`).
- Persistência: SQLite local (`agendamentos.sqlite`) usado pelo serviço de agendamento via SQLAlchemy.
- Observabilidade: logs de aplicação (`app.log`) e logs de auditoria JSON (`audit.log`) no serviço Flask; `morgan` e `console.log` no coordenador.

---

## Sistema Flask: Requisições, Modelos, Funcionamento

### Endpoints principais

- `GET /time`
  - Retorna o tempo do servidor em UTC (ISO-8601). Usado para sincronização de relógio (ex.: Algoritmo de Cristian).
  - Resposta: `{"time_utc": "..."}`

- `GET /telescopios`
  - Lista telescópios disponíveis (atualmente hard-coded).
  - Resposta: `{"telescopios": ["Hubble-Acad", "Kepler-Acad"]}`

- `GET /agendamentos`
  - Retorna todos os agendamentos persistidos no banco.

- `GET /agendamentos/<id>`
  - Retorna um agendamento específico (inclui links HATEOAS mínimos: `self` e `cancel`).

- `POST /agendamentos`
  - Fluxo resumido:
    1. Validação do JSON de entrada (`cientista_id`, `telescopio`, `horario_inicio_utc`).
    2. Monta `resource = f"{telescopio}_{horario}"` e solicita lock ao coordenador (`POST /lock/acquire`).
       - Se coordenador indisponível -> `503` (`coordinator-unavailable`).
       - Se coordenador rejeita (recurso ocupado) -> `409` (`resource-locked`).
    3. Se lock concedido, verifica no BD se existe conflito (`Agendamento.query.filter_by(...)`).
       - Se conflito detectado -> libera lock (best-effort) e retorna `409` (`conflict`).
    4. Persiste o agendamento, grava log de auditoria em JSON e tenta liberar o lock (`POST /lock/release`) em modo best-effort.
    5. Responde `201` com o recurso criado e links HATEOAS.

- `DELETE /agendamentos/<id>`
  - Remove o agendamento do DB, grava evento de auditoria e tenta liberar lock (best-effort).

### Modelos

- `Agendamento` (SQLAlchemy) — definido em `servico-agendamento/models.py`:
  - Campos: `id`, `cientista_id`, `telescopio`, `horario_inicio_utc`, `created_at`.
  - Método `to_dict()` para serialização (converte `created_at` para ISO-8601 + 'Z').

### Comportamento e observações de implementação

- O serviço delega gerenciamento de locks ao `servico-coordenador` (TTL + auto-release).
- Logs de auditoria são gravados em JSON (`audit.log`) com campos como `event_type`, `timestamp_utc` e `details` para rastreabilidade de negócio.
- Atenção para porta de execução: o arquivo `servico-agendamento/app.py` atualmente chama `app.run(..., port=5001)`. Garanta que o mapeamento de portas no `docker-compose.yml` esteja consistente (host -> container) para que os endpoints sejam acessíveis na porta correta do host.

---

## Sistema Node: Requisições, Funcionamento

### Endpoints do coordenador

- `POST /lock/acquire`
  - Corpo esperado: `{ "resource": "<resource>", "ttl_ms": <opcional> }`.
  - Comportamento:
    - Se já existe lock válido para o recurso -> retorna `409` (conflito).
    - Caso contrário, cria lock com TTL (padrão 5000ms), agenda liberação automática e retorna `{ "lockId": <n> }`.

- `POST /lock/release`
  - Corpo: `{ "resource": "<resource>" }`.
  - Remove o lock (se existir) e retorna `{ "released": true }` ou `404` se não existir.

- `GET /locks`
  - Endpoint de debug que lista locks ativos (útil para testes locais).

### Implementação e limitações

- O coordenador mantém locks em memória (`Map`) e usa `setTimeout` para auto-release — solução de protótipo, não tolerante a falhas.
- TTL padrão de 5000ms pode ser curto para redes com latência; pode ser ajustado com o parâmetro `ttl_ms`.
- Para produção, recomenda-se usar um armazenamento distribuído (Redis, etcd, Consul) e um protocolo de lock robusto.

---

## Prints de execução

- /telescopios

<img width="374" height="134" alt="image" src="https://github.com/user-attachments/assets/b4818bdb-3d26-4677-9580-12c640cc6978" />

- Criar Agendamento

<img width="1062" height="256" alt="image" src="https://github.com/user-attachments/assets/c47b0f8e-c650-4ce6-922c-a13d84f84330" />

- Conflito entre dois agendamentos sinalizado pelo coordenador

<img width="1073" height="117" alt="image" src="https://github.com/user-attachments/assets/5569921f-f0f3-45d8-98bc-3833e0582aea" />

- Deletar Agendamento

<img width="995" height="165" alt="image" src="https://github.com/user-attachments/assets/4683b3c4-33fc-44ec-84e0-6cb3253d5bae" />

- Log de Agendamentos

```
{"timestamp_utc": "2025-11-29T00:36:07.945583+00:00", "level": "AUDIT", "event_type": "AGENDAMENTO_CRIADO", "service": "servico-agendamento", "details": {"agendamento_id": 2, "cientista_id": 1, "horario_inicio_utc": "2026-02-01T00:00:00Z"}}
{"timestamp_utc": "2025-11-29T00:46:47.047766+00:00", "level": "AUDIT", "event_type": "AGENDAMENTO_CANCELADO", "service": "servico-agendamento", "details": {"agendamento_id": 1}}
```
- Interface para uso do Algoritmo de Cristian

<img width="1821" height="378" alt="image" src="https://github.com/user-attachments/assets/4f7c906e-380d-4a10-8541-e393f7c5c9e1" />



