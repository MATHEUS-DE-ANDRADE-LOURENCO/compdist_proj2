# API

Descrição dos endpoints principais implementados nesta entrega.

Base URL: `http://<host>:5000`

- GET `/time`
  - Descrição: Retorna o tempo oficial do servidor em UTC.
  - Resposta: `{"time_utc": "2025-10-26T18:00:05.123Z"}`

- GET `/telescopios`
  - Descrição: Lista telescópios disponíveis (nesta versão: Hubble-Acad, Kepler-Acad).

- GET `/agendamentos`
  - Descrição: Lista agendamentos.

- GET `/agendamentos/<id>`
  - Descrição: Recupera agendamento por id.

- POST `/agendamentos`
  - Descrição: Cria novo agendamento. Antes de salvar, solicita lock ao serviço coordenador.
  - Corpo: `{"cientista_id": 7, "telescopio": "Hubble-Acad", "horario_inicio_utc": "2025-12-01T03:00:00Z"}`
  - Resposta (201): Objeto agendamento + HATEOAS links, ex:
    - `links`: `{ "self": "/agendamentos/123", "cancel": "/agendamentos/123" }`
  - Erros:
    - 409: Recurso ocupado (lock não concedido ou conflito no BD)

- DELETE `/agendamentos/<id>`
  - Descrição: Cancela agendamento. Solicita liberação de lock ao coordenador.

Fluxo HATEOAS: respostas que criam/retornam recursos embutem links com próximas ações possíveis.