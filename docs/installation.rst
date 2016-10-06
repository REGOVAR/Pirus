============
Installation
============

You need to have [MongoDB](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/) and [RabbitMQ](https://www.rabbitmq.com/install-debian.html) installed on your system. 
.. code-block:: bash
    sudo apt install rabbitmq-server
    sudo apt install mongodb
    sudo apt install lxd
	
You may need also to install
.. code-block:: bash
    sudo apt install build-essential libssl-dev libffi-dev python3-dev virtualenv
	
        
You can then clone the repository and install requirements.
.. code-block:: bash
    git clone https://github.com/REGOVAR/Pirus.git
    cd Pirus
    virtualenv -p /usr/bin/python3.5 venv
    source venv/bin/activate
    pip install -r requirements.txt
 
