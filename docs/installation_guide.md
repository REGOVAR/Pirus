## Run Pirus

You can run Pirus on a fresh install of Ubuntu Xenial either on bare metal or in a container (see below).
The following commands starting with a `#` have to be run as root.

Install Pirus dependencies:
    
    # apt update && apt upgrade
    # apt install git ca-certificates nginx rabbitmq-server mongodb lxd build-essential libssl-dev libffi-dev python3-dev virtualenv
    
Setup lxd for Pirus containers (FIXME). `newgrp` permet d'ajouter un groupe à l'utilisateur courant (et non pas de créer un groupe).

    # newgrp lxd
    # lxd init

You have to configure LXD with `lxd init`:
* Name of the storage backend to use (dir or zfs): dir
* Would you like LXD to be available over the network (yes/no): no
* Do you want to configure the LXD bridge: yes
* Would you like to setup a network bridge for LXD containers now? Yes
* Bridge interface name: (keep default)
* Would you like to setup an IPv4 subnet? Yes
* IPv4 address: (keep default)
* IPv4 CIDR mask: (keep default)
* First DHCP address: (keep default)
* Last DHCP address: (keep default)
* Max number of DHCP clients: (keep default)
* Do you want to NAT the IPv4 traffic? No
* Do you want to setup an IPv6 subnet? No

Add an user account for Pirus and allow it to use lxd:

    # useradd pirus --create-home
    # usermod -a -G lxd pirus
    
Create Pirus directories:

    # mkdir -p /var/regovar/pirus/{cache,downloads,files,databases,pipelines,runs}
    # chown -R pirus:pirus /var/regovar/pirus
    
Launch a LXD container to get an Ubuntu Xenial image. This will generate a client certificate and make the subsequent container creations faster.
  
    # su pirus
    $ lxc launch images:ubuntu/xenial firstContainerToInitLxd
    $ lxc delete firstContainerToInitLxd --force
   
Get the Pirus source code and assets:   
    
    $ git clone https://github.com/REGOVAR/Pirus.git ~/Pirus
    $ cd ~/Pirus
    
Create a virtual environment to use Python 3.5 without conflicting with other setups:

    $ virtualenv -p /usr/bin/python3.5 venv
    
Activate the virtual environment:
    
    $ source venv/bin/activate
    
Install Pirus Python dependencies:    
    
    $ pip install -r requirements.txt
    
Launch Celery to keep track of jobs:

    $ cd pirus
    $ make cel &!
    
Launch Pirus itself:    
    
    $ make app &!
    
Leave the pirus user session (Celery and the Pirus application are still running); this leaves the virtual environment at the same time: 
    
    $ exit
    
Configure nginx as a reverse proxy for the Pirus application and static assets:
    
    # echo 'upstream aiohttp_pirus
    {
        server 127.0.0.1:8200 fail_timeout=0;
    }
    server
    {
        listen 80;
        listen [::]:80;

        location / {
            # Need for websockets
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_set_header Host $http_host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_redirect off;
            proxy_buffering off;
            proxy_pass http://aiohttp_pirus;
        }

        location /static {
            root /var/regovar/pirus;
        }
    }' > /etc/nginx/sites-available/pirus
    
Disable the "Welcome to nginx!" page on port 80:    
    
    # rm /etc/nginx/sites-enabled/default
    
Enable the pirus site in nginx on port 80:
    
    # ln -s /etc/nginx/sites-available/pirus /etc/nginx/sites-enabled
    
Restart nginx:    
    
    # service nginx restart

## Run Pirus in a container (optional and experimental)

### Run containers inside containers
You only to do this step once when you want to install Pirus for the first time.
   
    $ echo 'lxc.mount.auto = cgroup
    lxc.aa_profile = lxc-container-default-with-nesting' >> ~/.config/lxc/default.conf

"The first will cause the cgroup manager socket to be bound into the container, so that lxc inside the container is able to administer cgroups for its nested containers. The second causes the container to run in a looser Apparmor policy which allows the container to do the mounting required for starting containers. Note that this policy, when used with a privileged container, is much less safe than the regular policy or an unprivileged container." See [LXC documentation on Ubuntu help](https://help.ubuntu.com/lts/serverguide/lxc.html).

### Create a lxc container and start it
You need to do these steps every time you want to install Pirus in a container.

    $ lxc-create -n regovar_pirus -t download -- -d ubuntu -r xenial -a amd64
    $ lxc-start -n regovar_pirus
    $ lxc-attach -n regovar_pirus

### Restart a stopped container
If you have stopped a container either manually or by stopping the host computer, you can restart it.

    $ lxc-start -n regovar_pirus
    $ lxc-attach -n regovar_pirus
