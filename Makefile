.PHONY: install run clean test

install:
	uv venv || true
	uv pip install -e .

run:
	./run_flstudio_mcp.sh

clean:
	rm -rf .venv
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

test:
	.venv/bin/python fl_studio_controller/testing/test_suite.py
