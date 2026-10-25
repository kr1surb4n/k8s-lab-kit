// Minimal Express server with health endpoint and structured logging.
// Designed for k8s: graceful shutdown, health endpoint, env config.
const express = require('express');
const os = require('os');

const app = express();
const PORT = process.env.PORT || 3000;
const APP_NAME = process.env.APP_NAME || 'node-express';
const VERSION = process.env.VERSION || '1.0.0';

// JSON body parser
app.use(express.json());

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'info',
      msg: 'http_request',
      method: req.method,
      path: req.path,
      status: res.statusCode,
      duration_ms: Date.now() - start,
      pod: os.hostname(),
      app: APP_NAME,
      version: VERSION
    }));
  });
  next();
});

// Health endpoint for k8s probes
app.get('/healthz', (req, res) => {
  res.json({
    status: 'ok',
    app: APP_NAME,
    version: VERSION,
    hostname: os.hostname(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    timestamp: new Date().toISOString()
  });
});

// Readiness endpoint (can add DB/cache checks here)
app.get('/ready', (req, res) => {
  // Add dependency checks here (DB, cache, etc.)
  res.json({ status: 'ready', app: APP_NAME });
});

// Example API endpoint
app.get('/api/hello', (req, res) => {
  res.json({
    message: `Hello from ${APP_NAME}`,
    version: VERSION,
    pod: os.hostname(),
    env: process.env.APP_ENV || 'unknown'
  });
});

// Graceful shutdown
let shuttingDown = false;
const shutdown = (signal) => {
  console.log(JSON.stringify({ level: 'info', msg: `Received ${signal}, shutting down gracefully` }));
  shuttingDown = true;
  server.close(() => {
    console.log(JSON.stringify({ level: 'info', msg: 'Server closed' }));
    process.exit(0);
  });
  // Force exit after 30s
  setTimeout(() => process.exit(1), 30000);
};

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

const server = app.listen(PORT, () => {
  console.log(JSON.stringify({ level: 'info', msg: `Server listening on port ${PORT}`, app: APP_NAME }));
});