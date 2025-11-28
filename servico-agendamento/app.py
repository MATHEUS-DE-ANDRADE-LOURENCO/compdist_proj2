"""
servico-agendamento.app

Aplicação Flask que implementa a API de agendamento.

Funcionalidades principais:
- Endpoint `/time` para retornar o tempo oficial do servidor (UTC).
- Endpoints CRUD mínimos para `agendamentos` e `telescopios`.
- Integração com o serviço coordenador (locks) via HTTP (POST /lock/acquire e /lock/release).
- Logging de aplicação (app.log) e logging de auditoria (audit.log) no formato JSON.

Este arquivo contém comentários explicativos para cada parte crítica do fluxo
de agendamento, incluindo aquisição/liberação de locks, verificação de conflitos
no banco de dados (SQLite via SQLAlchemy) e geração de logs de auditoria.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timezone
import requests
from db import init_db, db
from models import Agendamento

COORDINATOR_URL = os.environ.get('COORDINATOR_URL', 'http://coordenador:3000')

def create_app():
    app = Flask(__name__)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'agendamentos.sqlite')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(db_path)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configuração de logging
    # - app.logger: logs de aplicação (texto) para depuração/observabilidade
    # - audit_logger: logs de auditoria (JSON) para eventos de negócio
    log_handler = RotatingFileHandler(os.path.join(base_dir, 'app.log'), maxBytes=5*1024*1024, backupCount=2)
    log_handler.setFormatter(logging.Formatter('%(levelname)s:%(asctime)s:%(name)s:%(message)s'))
    log_handler.setLevel(logging.INFO)
    app.logger.addHandler(log_handler)
    app.logger.setLevel(logging.INFO)

    # audit logger
    audit_handler = RotatingFileHandler(os.path.join(base_dir, 'audit.log'), maxBytes=5*1024*1024, backupCount=2)
    audit_handler.setFormatter(logging.Formatter('%(message)s'))
    audit_handler.setLevel(logging.INFO)
    audit_logger = logging.getLogger('audit')
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)

    init_db(app)

    telescopios = ['Hubble-Acad', 'Kepler-Acad']

    @app.route('/time', methods=['GET'])
    def time():
        # Retorna o tempo atual do servidor em UTC no formato ISO-8601.
        # Clientes usam este endpoint para aplicar o Algoritmo de Cristian
        # e estimar offset/latência antes de enviar pedidos de agendamento.
        now = datetime.now(timezone.utc).isoformat()
        app.logger.info('Requisição recebida para GET /time')
        return jsonify({'time_utc': now})

    @app.route('/telescopios', methods=['GET'])
    def listar_telescopios():
        # Lista telescópios disponíveis. Em versões futuras, isso pode vir do BD.
        return jsonify({'telescopios': telescopios})

    @app.route('/agendamentos', methods=['GET'])
    def listar_agendamentos():
        # Retorna todos os agendamentos registrados no banco.
        ags = Agendamento.query.all()
        return jsonify([a.to_dict() for a in ags])

    @app.route('/agendamentos/<int:aid>', methods=['GET'])
    def get_agendamento(aid):
        a = Agendamento.query.get(aid)
        if not a:
            return jsonify({'error': 'not found'}), 404
        d = a.to_dict()
        # Inclui links HATEOAS mínimos: self e cancel (DELETE).
        d['links'] = {'self': f'/agendamentos/{a.id}', 'cancel': f'/agendamentos/{a.id}'}
        return jsonify(d)

    @app.route('/agendamentos', methods=['POST'])
    def criar_agendamento():
        # Fluxo de criação de agendamento (POST /agendamentos):
        # 1) Valida campos obrigatórios no JSON de entrada.
        # 2) Solicita lock ao coordenador para o recurso (telescópio+horário).
        # 3) Se lock concedido, verifica no BD se já existe conflito.
        # 4) Se não houver conflito, persiste o agendamento, grava log de auditoria
        #    e libera o lock no coordenador (best-effort).
        app.logger.info('Requisição recebida para POST /agendamentos')
        data = request.get_json() or {}
        cientista_id = data.get('cientista_id')
        telescopio = data.get('telescopio')
        horario = data.get('horario_inicio_utc')

        # Validação básica de entrada
        if not all([cientista_id, telescopio, horario]):
            return jsonify({'error': 'missing fields'}), 400

        # O recurso protegido pelo lock é a combinação telescópio+horário.
        resource = f"{telescopio}_{horario}"
        app.logger.info(f'Tentando adquirir lock para o recurso {resource}')

        # Contato síncrono com o serviço coordenador para adquirir lock.
        try:
            r = requests.post(f"{COORDINATOR_URL}/lock/acquire", json={'resource': resource})
        except Exception as e:
            # Se o coordenador estiver indisponível, retornamos 503 (Service Unavailable).
            app.logger.error('Erro ao contatar coordenador: %s', e)
            return jsonify({'error': 'coordinator-unavailable'}), 503

        # Se o coordenador respondeu com erro (por exemplo 409), propagamos 409 para o cliente.
        if r.status_code != 200:
            app.logger.info('Falha ao adquirir lock, recurso ocupado')
            return jsonify({'error': 'resource-locked'}), 409

        # Lock concedido — agora garantimos que não há conflito no BD
        app.logger.info('Lock adquirido com sucesso')
        conflict = Agendamento.query.filter_by(telescopio=telescopio, horario_inicio_utc=horario).first()
        if conflict:
            # Se outro agendamento já existe, liberamos o lock e retornamos 409.
            app.logger.info('Conflito detectado no BD')
            try:
                requests.post(f"{COORDINATOR_URL}/lock/release", json={'resource': resource})
            except Exception:
                # É best-effort; se falhar, registramos mas não impedimos a resposta.
                pass
            return jsonify({'error': 'conflict'}), 409

        # Persistência do novo agendamento
        a = Agendamento(cientista_id=cientista_id, telescopio=telescopio, horario_inicio_utc=horario)
        db.session.add(a)
        db.session.commit()

        # Gerar log de auditoria (formato JSON) para rastreabilidade de negócio
        import json
        audit = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'level': 'AUDIT',
            'event_type': 'AGENDAMENTO_CRIADO',
            'service': 'servico-agendamento',
            'details': {'agendamento_id': a.id, 'cientista_id': cientista_id, 'horario_inicio_utc': horario}
        }
        audit_logger.info(json.dumps(audit))

        # Preparar resposta com links HATEOAS mínimos
        resp = a.to_dict()
        resp['links'] = {'self': f'/agendamentos/{a.id}', 'cancel': f'/agendamentos/{a.id}'}

        # Liberar lock no coordenador (best-effort): mesmo que a liberação falhe,
        # o lock no coordenador terá TTL e será liberado automaticamente.
        try:
            requests.post(f"{COORDINATOR_URL}/lock/release", json={'resource': resource})
        except Exception:
            app.logger.warning('Falha ao liberar lock no coordenador')

        return jsonify(resp), 201

    @app.route('/agendamentos/<int:aid>', methods=['DELETE'])
    def cancelar_agendamento(aid):
        a = Agendamento.query.get(aid)
        if not a:
            return jsonify({'error': 'not found'}), 404
        resource = f"{a.telescopio}_{a.horario_inicio_utc}"
        db.session.delete(a)
        db.session.commit()
        # audit log
        import json
        audit = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'level': 'AUDIT',
            'event_type': 'AGENDAMENTO_CANCELADO',
            'service': 'servico-agendamento',
            'details': {'agendamento_id': aid}
        }
        audit_logger.info(json.dumps(audit))
        # release lock (best-effort)
        try:
            requests.post(f"{COORDINATOR_URL}/lock/release", json={'resource': resource})
        except Exception:
            pass
        return jsonify({'status': 'cancelled'})

    @app.route('/interface', methods=['GET'])
    def interface():
        # Serve página estática de sincronização de tempo
        return send_from_directory(os.path.join(base_dir, 'static'), 'index.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
