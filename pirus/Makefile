init:
	pip install -r requirements.txt

clear:
	database_name=$$(sed -n 's/^\s*DATABASE_NAME\s*=\s*"\([^"]\+\)".*/\1/p' config.py) ; \
	sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$${database_name}'" ; \
	sudo -u postgres psql -c "DROP DATABASE $${database_name}" ; \
	sudo -u postgres psql -c "CREATE DATABASE $${database_name} OWNER pirus" ; \
	psql -U pirus -d $$database_name -f ../install/create_all.sql
	files_dir=$$(sed -n 's/^\s*FILES_DIR\s*=\s*"\([^"]\+\)".*/\1/p' config.py) ; \
	test $$files_dir && rm -rf $$files_dir/*
	temp_dir=$$(sed -n 's/^\s*TEMP_DIR\s*=\s*"\([^"]\+\)".*/\1/p' config.py) ; \
	test $$temp_dir && rm -rf $$temp_dir/*
	pipelines_dir=$$(sed -n 's/^\s*PIPELINES_DIR\s*=\s*"\([^"]\+\)".*/\1/p' config.py) ; \
	test $$pipelines_dir && rm -rf $$pipelines_dir/*
	jobs_dir=$$(sed -n 's/^\s*JOBS_DIR\s*=\s*"\([^"]\+\)".*/\1/p' config.py) ; \
	test $$jobs_dir && rm -rf $$jobs_dir/*

clear_lxd:
	lxc list | grep "pirus-job" | awk '{print $$2}' | xargs lxc delete --force
	lxc image list | grep "pirus-pipe-" | awk '{print $$2}' | xargs lxc image delete

test:
	database_name=$$(sed -n 's/^\s*DATABASE_NAME\s*=\s*"\([^"]\+\)".*/\1/p' config.py) ; \
	test -n "$${database_name}" && \
	sudo -u postgres psql -c "DROP DATABASE IF EXISTS $${database_name}_test" && \
	sudo -u postgres psql -c "CREATE DATABASE $${database_name}_test OWNER pirus" && \
	psql -U pirus -d $${database_name}_test -f ../install/create_all.sql && \
	psql -U pirus -d $${database_name}_test -f tests/init_fake_data.sql && \
	sed -i.bak 's/^\(\s*DATABASE_NAME\s*=\s*"[^"]\+\)\(".*\)/\1_test\2/' config.py && \
	python tests.py && \
	mv config.py config.test && \
	mv config.py.bak config.py && \
	sudo -u postgres psql -c "DROP DATABASE IF EXISTS $${database_name}_test"


install:
	pirus_uid=$$(id -u pirus) ; \
	pirus_gid=$$(id -g pirus) ; \
	lxd_uid=$$(awk -F : '/lxd/ { print $$2 }' /etc/subuid) ; \
	lxd_gid=$$(awk -F : '/lxd/ { print $$2 }' /etc/subgid) ; \
	< ../install/config.default > config.py sed " \
		s/\(^\s*PIRUS_UID\s*=\s*\)[0-9]\+/\1$$pirus_uid/ ; \
		s/\(^\s*PIRUS_GID\s*=\s*\)[0-9]\+/\1$$pirus_gid/ ; \
		s/\(^\s*LXD_UID\s*=\s*\)[0-9]\+/\1$$lxd_uid/ ; \
		s/\(^\s*LXD_GID\s*=\s*\)[0-9]\+/\1$$lxd_gid/ ; \
	"
	# To be done in the install script to allow user to see uid/guid that have been retrieved.
	echo "Don't forget to update the config.py file with your settings"
	../install/install.sh
	


# > pirus.out 2>pirus_error.out  &
app:
	python pirus_server.py

stop:
	ps -ef | grep pirus_server | awk '{print $$2}'  | xargs sudo kill -9

.PHONY: init test app stop clear
