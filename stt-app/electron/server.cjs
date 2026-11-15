const { createServer } = require('node:http');
const path = require('node:path');
const next = require('next');

const port = Number(process.env.PORT || process.env.PBL6_STT_PORT || '3100');
const appDir = path.resolve(__dirname, '..');

const app = next({ dev: false, dir: appDir });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const server = createServer((req, res) => {
    handle(req, res);
  });

  server.on('error', (err) => {
    console.error('Next.js HTTP server error:', err);
    process.exit(1);
  });

  server.listen(port, '127.0.0.1', () => {
    if (process.send) {
      process.send({ type: 'ready', port });
    }
  });

  const stop = () => {
    server.close(() => process.exit(0));
  };
  process.on('SIGTERM', stop);
  process.on('SIGINT', stop);
}).catch((err) => {
  console.error('Failed to start Next.js server:', err);
  process.exit(1);
});
