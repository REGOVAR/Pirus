# Pirus-Server

Pirus is an application launcher service which allow user to run pipeline code from a remote REST client. Each pipeline are provided as plugin made by the community. Pirus runs code in a LXC container to keep your server safe.   


## Installation 
You need to have [MongoDB](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/) and [RabbitMQ](https://www.rabbitmq.com/install-debian.html) installed on your system. 

        sudo apt install rabbitmq-server
        sudo apt install mongodb
        sudo apt install lxd
	
You may need also to install

	sudo apt install build-essential libssl-dev libffi-dev python3-dev virtualenv
	
        
You can then clone the repository and install requirements.

	git clone https://github.com/REGOVAR/Pirus.git
	cd Pirus
	virtualenv -p /usr/bin/python3.5 venv
	source venv/bin/activate
	pip install -r requirements.txt 


Create your first lxd pipeline for pirus.

	# create a container
	lxc launch images:ubuntu/xenial pirus
	# configure it
	lxc exec pirus -- /bin/bash
	
	# following directories are mandatory
	mkdir /pipeline/run
	mkdir /pipeline/inputs
	mkdir /pipeline/outputs
	mkdir /pipeline/logs
	mkdir /pipeline/db
	
	# need curl if you want to notify server with the progress of your run
	apt install curl
	
	# the script run.sh is the "entry point" of your run
	echo "curl ${NOTIFY}50" > /pipeline/run/run.sh
	echo "ls -l /pipeline/database/db > /pipeline/outputs/result.txt" >> /pipeline/run/run.sh
	chmod +x /pipeline/run/run.sh
	
	# exit the container
	exit
	
	# stop it and create an image
	lxc stop pirus
	lxc publish pirus --alias=PirusSimple
	
	
	

## Run pirus 

Your need first to run celery 

	cd pirus/
	celery worker -A pirus_worker --loglevel=info -Q PirusQueue

So you can run pirus 

	python app.y 

Check if pirus is working there : http://localhost:8080/v1/www
	
