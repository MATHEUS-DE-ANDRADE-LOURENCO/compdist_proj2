/**
 * servico-coordenador/server.js
 *
 * Serviço simples de locks (coordenador). Fornece endpoints HTTP para:
 * - POST /lock/acquire  -> tenta adquirir um lock para um recurso
 * - POST /lock/release  -> libera um lock (best-effort)
 * - GET  /locks          -> lista locks ativos (para debug)
 *
 * Implementação em memória (Map). Cada lock possui um TTL e é liberado
 * automaticamente após expirar. Esta é uma implementação de protótipo —
 * em produção seria necessário um armazenamento distribuído e consistente
 * (Redis, etcd, Consul) para tolerância a falhas.
 */

const express = require('express');
const bodyParser = require('body-parser');
const morgan = require('morgan');

const app = express();
// bodyParser para ler JSON de requests
app.use(bodyParser.json());
// morgan para logs de acesso no formato combinado
app.use(morgan('combined'));

// Tabela de locks em memória: resource -> { lockId, expiresAt }
const locks = new Map();
let nextLockId = 1;

function nowMs() { return Date.now(); }

// Endpoint para adquirir lock
app.post('/lock/acquire', (req, res) => {
  const { resource, ttl_ms } = req.body || {};
  if (!resource) return res.status(400).json({ error: 'missing resource' });

  // Se já existe um lock válido, rejeitamos com 409 (conflito)
  const entry = locks.get(resource);
  if (entry && entry.expiresAt > nowMs()) {
    return res.status(409).json({ error: 'locked' });
  }

  // Cria novo lock com TTL (padrão 5000ms)
  const lockId = nextLockId++;
  const ttl = ttl_ms || 5000;
  const expiresAt = nowMs() + ttl;
  locks.set(resource, { lockId, expiresAt });

  // Agendamos liberação automática como proteção contra clientes que não liberam
  setTimeout(() => {
    const cur = locks.get(resource);
    if (cur && cur.lockId === lockId && cur.expiresAt <= nowMs()) {
      locks.delete(resource);
      console.log(`Auto-released lock ${resource}`);
    }
  }, ttl + 10);

  // Retornamos um identificador simples de lock. Clientes não precisam usar
  // este ID para liberar na versão atual, mas é útil para rastreabilidade.
  return res.json({ lockId });
});

// Endpoint para liberar lock (best-effort). Se o lock não existir, retorna 404.
app.post('/lock/release', (req, res) => {
  const { resource } = req.body || {};
  if (!resource) return res.status(400).json({ error: 'missing resource' });
  if (locks.has(resource)) {
    locks.delete(resource);
    return res.json({ released: true });
  }
  return res.status(404).json({ released: false });
});

// Endpoint de inspeção para debug local — lista os locks ativos
app.get('/locks', (req, res) => {
  const out = {};
  for (const [k,v] of locks.entries()) out[k] = v;
  res.json(out);
});

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Coordinator listening on ${port}`));
