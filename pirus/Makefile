init:
	pip install -r requirements.txt

clear:
	sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'pirus'"
	sudo -u postgres psql -c "DROP DATABASE pirus"
	sudo -u postgres psql -c "CREATE DATABASE pirus OWNER pirus"
	psql -U pirus -d pirus -f ../install/create_all.sql
	rm -rf /var/regovar/pirus/files/*
	rm -rf /var/regovar/pirus/downloads/*
	rm -rf /var/regovar/pirus/pipelines/*
	rm -rf /var/regovar/pirus/jobs/*


test:
	sudo -u postgres psql -c "DROP DATABASE IF EXISTS pirus_test"
	sudo -u postgres psql -c "CREATE DATABASE pirus_test OWNER pirus"
	psql -U pirus -d pirus_test -f ../install/create_all.sql
	psql -U pirus -d pirus_test -f tests/init_fake_data.sql
	sed -i.bak s/DATABASE_NAME\ =\ \"pirus\"/DATABASE_NAME\ =\ \"pirus_test\"/g config.py
	python tests.py
	mv config.py config.test
	mv config.py.bak config.py
	sudo -u postgres psql -c "DROP DATABASE IF EXISTS pirus_test"


install:
	cp ../install/config.default config.py
	echo "Don't forget to update the config.py file with your settings"



app:
	python pirus_server.py > pirus.out 2>pirus_error.out  &

stop:
	ps -ef | grep pirus_server | awk '{print $$2}'  | xargs sudo kill -9

.PHONY: init test app stop clear
