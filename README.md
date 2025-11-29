# Projeto SCTec - Serviço de Agendamento

Matheus de Andrade Lourenço; 
Murillo Cardoso Ferreira; 
Pietro Zanaga Neto <br>
Esta implementação contém:

- `servico-agendamento`: API Flask (porta 5000)
- `servico-coordenador`: Serviço de locks em Node.js (porta 3000)
- Dockerfiles e `docker-compose.yml` para orquestração

Execução rápida com Docker Compose:

```bash
docker compose up --build
```

Depois, sincronize o relógio com `GET /time` e faça pedidos a `POST /agendamentos`.

Para teste de concorrência (local):

```bash
python3 servico-agendamento/stress_test.py --workers 10 --requests 50
```

Arquivos de documentação: `MODELOS.md`, `API.md`, `LOGGING.md`.# compdist_proj2
