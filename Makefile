.PHONY: install dev test clean db-up db-down db-init docker-up docker-down docker-build docker-logs format lint

install:
	pip install -e ".[dev]"

dev:
	python app/main.py

test:
	pytest

test-cov:
	pytest --cov=app --cov=models --cov=services --cov-report=html

# Docker commands
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose up -d --build

docker-logs:
	docker-compose logs -f

docker-init: docker-up
	@echo "Waiting for services to be ready..."
	@sleep 5
	docker-compose exec app python scripts/init_db.py

# Legacy database commands (for local development)
db-up:
	docker-compose up -d postgres

db-down:
	docker-compose down

db-init:
	python scripts/init_db.py

format:
	black app/ models/ services/ tests/

lint:
	flake8 app/ models/ services/
	mypy app/ models/ services/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov .hypothesis
