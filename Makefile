.PHONY: dev down seed test

dev:
	docker compose up --build

down:
	docker compose down

seed:
	docker compose exec backend python seed.py

test:
	docker compose exec backend python -m pytest tests/ -v

test-local:
	cd backend && pip install -r requirements.txt -q && python -m pytest tests/ -v
