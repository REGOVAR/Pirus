init:
	pip install -r requirements.txt

test:
	python tests.py

app:
	python pirus_server.py

cel:
	celery worker -A pirus_celery --loglevel=info -Q PirusQueue

.PHONY: init test app cel
