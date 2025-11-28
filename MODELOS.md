# MODELOS

Entidades principais do serviço de agendamento.

- Agendamento
  - `id` (integer, PK)
  - `cientista_id` (integer)
  - `telescopio` (string)
  - `horario_inicio_utc` (ISO8601 string)
  - `created_at` (UTC timestamp)

- Cientista (modelo leve)
  - `id` (integer, PK)
  - `nome` (string)

- Telescópio (lista estática nesta versão)
  - `nome` (string)

Notas:
- O `Agendamento` é a fonte autoritativa do tempo reservado.
- Conflitos são definidos por horários idênticos para o mesmo telescópio.