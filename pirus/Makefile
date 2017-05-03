init:
	pip install -r requirements.txt

clear_db:
	psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'pirus'"
	psql -U postgres -c "DROP DATABASE pirus"
	psql -U postgres -c "CREATE DATABASE pirus OWNER pirus"
	psql -U pirus -d pirus -f ../install/create_all.sql

test:
	# psql -U postgres -c "DROP DATABASE IF EXISTS pirus_test"
	# psql -U postgres -c "CREATE DATABASE pirus_test OWNER pirus"
	# psql -U pirus -d pirus_test -f ../install/create_all.sql
	# psql -U pirus -d pirus_test -f tests/init_fake_data.sql
	# sed -i.bak s/DATABASE_NAME\ =\ \"pirus\"/DATABASE_NAME\ =\ \"pirus_test\"/g config.py
	python tests.py
	# mv config.py config.test
	# mv config.py.bak config.py
	# psql -U postgres -c "DROP DATABASE IF EXISTS pirus_test"


install:
	cp ../install/config.default config.py
	echo "Don't forget to update the config.py file with your settings"



app:
	python pirus_server.py

cel:
	celery worker -A pirus_celery --loglevel=info -Q PirusQueue

.PHONY: init test app cel
