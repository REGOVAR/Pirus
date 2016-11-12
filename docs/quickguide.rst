Quick guide
###########

Deploye and use Pirus in 5 minutes.


Installation
============



You need to have `MongoDB <https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/>`_ and `RabbitMQ <https://www.rabbitmq.com/install-debian.html>`_ installed on your system :: 

        sudo apt install rabbitmq-server
        sudo apt install mongodb
        sudo apt install lxd
	
You may need also to install ::

        sudo apt install build-essential libssl-dev libffi-dev python3-dev virtualenv
	
        
You can then clone the repository and install requirements ::

        git clone https://github.com/REGOVAR/Pirus.git
        cd Pirus
        virtualenv -p /usr/bin/python3.5 venv
        source venv/bin/activate
        pip install -r requirements.txt


	

Run pirus
=========

Your need first to run celery ::

	cd pirus/
	celery worker -A pirus_worker --loglevel=info -Q PirusQueue

So you can run pirus ::

	python app.y 

Check if pirus is working there : http://localhost:8080/v1/www
 



Upload a file
=============

todo


Install a Pipeline
==================


todo



Launch a Run
============

todo




