## Run Pirus in a container (optional)

### Run containers inside containers
You only to do this step once when you want to install Pirus for the first time.
   
    $ echo 'lxc.mount.auto = cgroup
    lxc.aa_profile = lxc-container-default-with-nesting' >> ~/.config/lxc/default.conf

"The first will cause the cgroup manager socket to be bound into the container, so that lxc inside the container is able to administer cgroups for its nested containers. The second causes the container to run in a looser Apparmor policy which allows the container to do the mounting required for starting containers. Note that this policy, when used with a privileged container, is much less safe than the regular policy or an unprivileged container." See [LXC documentation on Ubuntu help](https://help.ubuntu.com/lts/serverguide/lxc.html)

### Create a lxc container and start it
You need to do these steps every time you want to install Pirus in a container.

    $ lxc-create -n regovar_pirus -t download -- -d ubuntu -r xenial -a amd64
    $ lxc-start -n regovar_pirus
    $ lxc-attach -n regovar_pirus
    
### Restart a stopped container
If you have stopped a container either manually or by stopping the host computer, you can restart it.

    $ lxc-start -n regovar_pirus
    $ lxc-attach -n regovar_pirus
    
## Pirus

Installation script for Pirus on a fresh Ubuntu Xenial:
    # apt update && apt upgrade
    # apt install git ca-certificates nginx rabbitmq-server mongodb lxd build-essential libssl-dev libffi-dev python3-dev virtualenv
    # newgrp lxd
    # lxd init
    # useradd pirus --create-home
    # sudo usermod -a -G lxd pirus
    # mkdir -p /var/regovar/pirus/{cache,downloads,files,databases,pipelines,runs}
    # chown -R pirus:pirus /var/regovar/pirus
    # su pirus
    $ lxc launch images:ubuntu/xenial firstContainerToInitLxd
    $ lxc delete firstContainerToInitLxd --force
    $ git clone https://github.com/REGOVAR/Pirus.git ~/Pirus
    $ cd ~/Pirus
    $ virtualenv -p /usr/bin/python3.5 venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt
    $ cd pirus
    $ make cel &!
    $ make app &!
    $ exit
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
    # rm /etc/nginx/sites-enabled/default
    # ln -s /etc/nginx/sites-available/pirus /etc/nginx/sites-enabled
    # /etc/init.d/nginx restart
