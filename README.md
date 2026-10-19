# AudioCodes Syslog SIP Visualizer

Python webapplicatie om AudioCodes syslog-bestanden met SIP-berichten te parsen en te visualiseren als interactief SIP ladder diagram.

## Functies

- Upload van `.log`, `.txt` of `.syslog` bestanden
- Parsing van AudioCodes syslog-formaat met `[S=...]` en `[SID=...]`
- Multiline SIP-bericht extractie (requests en responses)
- Sessielijst met filters op SID, Call-ID, From, To en SIP method
- SIP call flow ladder diagram per sessie
- Message detail pane met headers en raw SIP tekst
- Dark mode
- Export call flow als TXT

## AudioCodes syslog formaat

Typische regel:

```
11:36:54.582  10.15.45.49  local0.notice  [S=12614840] [SID=50e91b:74:353424]  OPTIONS sip:example.com SIP/2.0
```

SIP-berichten kunnen direct na de header starten of na een richting-marker:

```
---- Outgoing SIP Message to 52.114.75.24:5061 from SIPInterface #2 (Teams) ----
INVITE sip:user@example.com SIP/2.0
...
```

Zie [AudioCodes SIP Call Session Logs](https://techdocs.audiocodes.com/utilities/syslog-viewer/Content/SyslogViewer/SIP%20Call%20Session%20Logs.htm) voor meer details.

## Lokale ontwikkeling

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Tests

```bash
cd backend
pytest
```

## Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000/api/health

## API endpoints

| Method | Endpoint | Beschrijving |
|--------|----------|--------------|
| POST | `/api/uploads` | Parse een syslog bestand en geef de sessies terug. Er wordt niets opgeslagen. |
| GET | `/api/health` | Health check |

## Projectstructuur

```
syslog-tool/
├── backend/          FastAPI + parsers
├── frontend/         React + TypeScript + Tailwind
└── docker-compose.yml
```

## Tips

- Gebruik geanonimiseerde productiebestanden om edge cases te valideren (firmwareversies, split messages).
- Sample testdata staat in `backend/tests/fixtures/sample_audiocodes.syslog`.
