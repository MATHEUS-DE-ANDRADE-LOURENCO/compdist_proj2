"""
db.py

Inicialização do SQLAlchemy para o serviço de agendamento.

Este módulo encapsula a criação do objeto `db` e a função `init_db` que
deve ser chamada passando a aplicação Flask. A função `init_db` garante que
as tabelas sejam criadas quando a aplicação iniciar (útil para desenvolvimento).
"""

from flask_sqlalchemy import SQLAlchemy

# Instância de SQLAlchemy compartilhada entre modelos e app
db = SQLAlchemy()


def init_db(app):
    """Inicializa o SQLAlchemy com a app Flask e cria as tabelas.

    Em produção, a criação automática de tabelas deve ser controlada por
    migrações (Alembic/Flyway/etc.). Aqui usamos `create_all()` apenas
    para simplificar o ambiente de desenvolvimento.
    """
    db.init_app(app)
    with app.app_context():
        db.create_all()
