Quick guide
###########

Deploye and use Pirus in 5 minutes. In the below tutorial :
 * <HOST> : is the server host, by example "www.pirus.com"
 * <PORT> ! is the port that will be use by the pirus python application, by example 8080
 * <PIRUS_PATH> : is the path on the server where is deployed the pirus python application, by example "/var/pirus"



Installation
============


You need to have `MongoDB <https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/>`_ and `RabbitMQ <https://www.rabbitmq.com/install-debian.html>`_ installed on your system :: 

        sudo apt install rabbitmq-server
        sudo apt install mongodb
        sudo apt install lxd
        sudo apt install nginx
	
	
You may need also to install ::

        sudo apt install build-essential libssl-dev libffi-dev python3-dev virtualenv
	
        
You can then clone the repository and install requirements ::

        git clone https://github.com/REGOVAR/Pirus.git
        cd <PIRUS_PATH>
        virtualenv -p /usr/bin/python3.5 venv
        source venv/bin/activate
        pip install -r requirements.txt


Using NginX
-----------
Create the file  into `/etc/nginx/sites-available/pirus` with the following content

Replace <PORT> and <HOST> with the good value::

	#
	# Virtual Host configuration for <HOST>
	#
	upstream aiohttp_pirus 
	{
	    server 127.0.0.1:<PORT> fail_timeout=0;
	}
	server 
	{
	    listen 80;
	    listen [::]:80;
	    server_name <HOST>;

	    location / {
		proxy_set_header Host $http_host;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_redirect off;
		proxy_buffering off;
		proxy_pass http://aiohttp_pirus;
	    }

	    location /static {
		root <PIRUS_PATH>/pirus/templates;
		#TODO : add path to run/files directories
	    }
	}

Enable this virtual host by creating a symbolic link ::

	sudo ln -s /etc/nginx/sites-enable/pirus /etc/nginx/sites-available/pirus 
	sudo /etc/init.d/nginx restart
	

Installing genomic databases
----------------------------
According to the config file of the Pirus application, you will install databases in the folder /var/pirus/databases by examples. You have to put in this directory all heavy databases used by pipes. The organisation shall stay simple, one folder by reference  ::

	/var/pirus/databases
		/hg19
			hg19.fa
			1000g.vcf.gz
			1000g.vcf.gz.tbi
			... <- all other files that could be used by pipelines
		/hg38
			hg38.fa
			...
		
Below the command to get all files for hg19 from the gatk public repository ::

	mkdir -p /var/pirus/databases/hg19
	cd /var/pirus/databases/hg19
	nohup wget ftp://gsapubftp-anonymous@ftp.broadinstitute.org/bundle/hg19/ -r &
	# nohup allow the long task to run without bocking your shell session
	# you can follow the execution by looking the log
	tail -f nohup.out
	# when all download are completed
	mv ftp.broadinstitute.org/bundle/hg19/* .
	
	# Check that file are not corrupted
	cat *.md5 >> all.md5
	sed -i 's/humgen\/gsa-scr1\/pub\/bundle\/2.8\/hg19/var\/pirus\/databases\/hg19/' all.md5
	md5sum -c all.md5
	
	# Unfortunately, all gz file in the gatk ftp are not in bzip format... so, to be used 
	# by bioinformatic's pipelines, we need to redo compression with the good algorithm
	# To get the bzip tool, you need to get and compile Htslib (https://github.com/samtools/htslib)
	unzip *.vcf.gz
	rm *.vcf.idx.gz
	rm *.vcf.gz
	<PATH_TO_HTSLIB_BIN>/bgzip *.vcf
	<PATH_TO_HTSLIB_BIN>/tabix -p *.vcf.gz
	
	

Run pirus
---------

Your need first to run celery ::

	cd pirus/
	celery worker -A pirus_worker --loglevel=info -Q PirusQueue

So you can run pirus web api ::

	python application.py 

Check if pirus is working there : http://localhost:8080/v1/www

You can also test pirus direclty from command line by using the `pirus` executable file ::

	$: pirus file list 


Using Pirus
===========

Upload a file
-------------

todo


Install a Pipeline
------------------


todo



Launch a Run
------------

todo




