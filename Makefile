.PHONY: install dev test clean db-up db-down format lint

install:
	pip install -e ".[dev]"

dev:
	python app/main.py

test:
	pytest

test-cov:
	pytest --cov=app --cov=models --cov=services --cov-report=html

db-up:
	docker-compose up -d postgres

db-down:
	docker-compose down

format:
	black app/ models/ services/ tests/

lint:
	flake8 app/ models/ services/
	mypy app/ models/ services/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov .hypothesis
