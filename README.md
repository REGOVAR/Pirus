# Pirus-Server

Pirus is an application launcher service which allow user to run pipeline code from a remote REST client. Each pipeline are provided as plugin made by the community. Pirus runs code in a LXC container to keep your server safe.   


## Installation 
You need to have [MongoDB](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/)
 and [RabbitMQ](https://www.rabbitmq.com/install-debian.html) installed on your system. 

        sudo apt install rabbitmq-server
        sudo apt install mongodb
        
You can then clone the repository and install requirements.

	git clone https://github.com/REGOVAR/Pirus.git
	cd Pirus
	virtualenv -p /usr/bin/python3.5 venv
	source venv/bin/activate
	pip install -r requirements.txt 

## Run pirus 

Your need first to run celery 

	cd pirus/
	celery worker -A tasks_manager --loglevel=info -Q MyPluginQueue

So you can run pirus 

	python app.y 

Check if pirus is working there : http://localhost:8080/www
	
