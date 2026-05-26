# Web Quickstart (Backend + Frontend)

## Nova estrutura

- `backend/`: API FastAPI para expor rota e disparar calculo Python
- `frontend/`: interface React (Vite + Leaflet)
- `main.py`: calculo original (mantido)
- `input.json` e `output.json`: contrato de entrada/saida do motor

## 1) Subir backend

No diretorio raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r backend\requirements.txt
python -m uvicorn backend.app.main:app --reload --port 8000
```

Endpoints:

- `GET /api/health`
- `GET /api/route`
- `POST /api/calculate`
- `POST /api/options`

Se `python` nao estiver no PATH do Windows, use o executavel completo:

```powershell
C:/Users/ailto/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pip install -r requirements.txt
C:/Users/ailto/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pip install -r backend/requirements.txt
C:/Users/ailto/AppData/Local/Python/pythoncore-3.14-64/python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

## 2) Subir frontend

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abra: `http://localhost:5173`

## 3) Fluxo de uso

1. Front carrega `GET /api/route` para mostrar o ultimo resultado.
2. Botao "Recalcular no Python" chama `POST /api/calculate`.
3. API executa `main.py` na raiz e devolve o novo `output.json`.

## 4) Ajuste de ambiente opcional

Se quiser apontar o frontend para outra URL da API, crie:

`frontend/.env`

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 5) Observacoes

- O backend espera `input.json` e escreve em `output.json` na raiz.
- Se os dados em `data/` nao estiverem presentes, o calculo pode falhar no `POST /api/calculate`.
- O frontend mostra `edges`, `segments` e `resumo` do JSON atual.
