.PHONY: help install install-dev test test-cov lint format type-check clean run-examples setup-pre-commit

help:
	@echo "Available commands:"
	@echo "  make install         Install project dependencies"
	@echo "  make install-dev     Install project with development dependencies"
	@echo "  make test           Run tests"
	@echo "  make test-cov       Run tests with coverage report"
	@echo "  make lint           Run linter (ruff)"
	@echo "  make format         Format code with black"
	@echo "  make type-check     Run type checking with mypy"
	@echo "  make clean          Clean up generated files"
	@echo "  make run-examples   Run example scripts"
	@echo "  make setup-pre-commit Install pre-commit hooks"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/ examples/

format:
	black src/ tests/ examples/
	ruff check --fix src/ tests/ examples/

type-check:
	mypy src/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

run-examples:
	@echo "Running basic usage examples..."
	python examples/basic_usage.py
	@echo "\nRunning research assistant example..."
	python examples/research_assistant.py

setup-pre-commit:
	pre-commit install
	pre-commit run --all-files

all: clean install-dev setup-pre-commit format lint type-check test