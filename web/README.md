# web/ — API e webapp (M7)
API **Hono** (sola lettura sul DB + ripartenza dopo il soft stop) e webapp **React** installabile (PWA), servite insieme su `http://127.0.0.1:8787`, **solo in locale**. L'accesso remoto arriverà con Cloudflare Tunnel e Access (M9), mai con una porta aperta.

```bash
npm install
npm run build        # webapp in web/dist
npm start            # API + webapp su 127.0.0.1:8787
npm run dev          # sviluppo: Vite (5173) con proxy verso l'API
npm test && npm run typecheck
```

| Endpoint | Contenuto |
|---|---|
| `GET /api/health` | ultimo heartbeat per componente, freschezza dei prezzi |
| `GET /api/accounts` | conti paper: valore, rendimento, drawdown, ordini, rifiuti per guardrail |
| `GET /api/accounts/:id/equity · positions · orders · events` | andamento, posizioni, ordini (con l'ombra Alpaca), ledger leggibile |
| `GET /api/guardrails` | limiti attivi da `config/guardrails.toml` |
| `POST /api/accounts/:id/resume` | ripartenza dopo il soft stop (G-01) tramite `money-engine resume`; richiede l'header `x-money-action: resume` (anti-CSRF) |

I numeri contabili vengono **solo** dal ledger e dal motore: la webapp li mostra, non li calcola. Le posizioni sono un riepilogo dei fill, solo per visualizzazione.
