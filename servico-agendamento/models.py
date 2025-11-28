"""
models.py

Modelos de domínio utilizados pelo serviço de agendamento.

Atualmente contém apenas o modelo `Agendamento` usado para persistir
reservas de tempo no telescópio. O modelo é simples para facilitar os
testes e a revisão do projeto.
"""

from datetime import datetime
from db import db


class Agendamento(db.Model):
    """Representa um agendamento reservado por um cientista.

    Campos:
    - id: chave primária auto-incremental
    - cientista_id: identificador do cientista solicitante
    - telescopio: nome do telescópio (string)
    - horario_inicio_utc: horário de início reservado (string ISO-8601)
    - created_at: timestamp UTC de criação (datetime)
    """
    __tablename__ = 'agendamentos'
    id = db.Column(db.Integer, primary_key=True)
    cientista_id = db.Column(db.Integer, nullable=False)
    telescopio = db.Column(db.String(128), nullable=False)
    horario_inicio_utc = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Serializa o modelo para dicionário JSON-serializável.

        Observação: `created_at` é convertido para string ISO-8601 com sufixo 'Z'.
        """
        return {
            'id': self.id,
            'cientista_id': self.cientista_id,
            'telescopio': self.telescopio,
            'horario_inicio_utc': self.horario_inicio_utc,
            'created_at': self.created_at.isoformat() + 'Z'
        }
