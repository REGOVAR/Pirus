# Pirus-Server

## Installation 

	git clone https://github.com/REGOVAR/Pirus.git
	cd Pirus
	virtualenv -p /usr/bin/python3.5 venv
	source venv/bin/activate
	pip install -r requirements.txt 

## Run pirus 

Your first need to run celery 

	cd pirus/
	celery worker -A tasks_manager --loglevel=info -Q MyPluginQueue

Then you can run pirus 

	python app.y 

Check if pirus is working there : http://localhost:8080/www
	
