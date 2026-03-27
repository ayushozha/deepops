# demo-app

DeepOps が監視対象として叩くための最小 FastAPI アプリです。

## Endpoints

- `GET /health`
- `GET /healthz`
- `GET /errors`
- `DELETE /errors`
- `GET /calculate/{value}`
- `GET /calculate/{a}/{b}`
- `GET /user/{username}`
- `GET /search?q=test`

## Intentional Bugs

- `/calculate/0`
  divide by zero
- `/user/unknown`
  missing user access
- `/search`
  blocking `time.sleep(5)`

これらの未処理例外は in-memory の `ERROR_BUFFER` に記録され、`/errors` から取得できます。

## Run

```bash
cd demo-app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --app-dir . --host 127.0.0.1 --port 8001 --reload
```

DeepOps backend の既定値は `http://localhost:8001` を見ます。

## Trigger A Demo Error

`trigger_error.py` で既定の 3 パターンを起こせます。

```bash
cd demo-app
source .venv/bin/activate
python trigger_error.py calculate_zero
python trigger_error.py user_missing
python trigger_error.py search_timeout
```

DeepOps backend にそのまま incident として入れたい場合:

```bash
python trigger_error.py calculate_zero --ingest
python trigger_error.py all --ingest
```

既定 URL:

- demo app: `http://127.0.0.1:8001`
- DeepOps backend: `http://127.0.0.1:8000`

## 60-Second Pitch Script

`pitch.sh` は 1 分デモ向けの台本と実行補助です。

```bash
cd demo-app
./pitch.sh
./pitch.sh check
./pitch.sh run
```
