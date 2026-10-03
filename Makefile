# UVERA — developer shortcuts. On Windows without make, run the commands by hand (see README).
.PHONY: setup data api web test lint check

setup:
	pip install -c constraints.txt -e "./ml[dev]" -e "./backend[dev]"
	cd frontend && npm install

data:
	python scripts/build_dev_artifacts.py

api:
	cd backend && uvicorn app.main:app --port 8000

web:
	cd frontend && npm run dev

lint:
	ruff check ml backend
	cd frontend && npm run lint

test:
	pytest -q ml/tests
	cd backend && pytest -q

check: lint test
	cd frontend && npm run build
