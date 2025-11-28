# LOGGING

Este documento define o formato mínimo para logs de aplicação e de auditoria.

1) Log de aplicação (texto):

- Formato: `LEVEL:TIMESTAMP:service:mensagem`
- Exemplo: `INFO:2025-10-26T18:00:04.500Z:servico-agendamento:Requisição recebida para POST /agendamentos`

2) Log de auditoria (JSON):

Cada evento de negócio importante (criação/cancelamento de agendamento) deve gerar um JSON séria:

```
{
  "timestamp_utc": "2025-10-26T18:00:05.123Z",
  "level": "AUDIT",
  "event_type": "AGENDAMENTO_CRIADO",
  "service": "servico-agendamento",
  "details": {
    "agendamento_id": 123,
    "cientista_id": 7,
    "horario_inicio_utc": "2025-12-01T03:00:00Z"
  }
}
```

Observações:
- Logs de aplicação vão para `app.log`; logs de auditoria para `audit.log`.
- Em produção, os arquivos podem ser direcionados a um agregador (ELK, Fluentd, etc.).