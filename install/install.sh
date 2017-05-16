#!/bin/sh


DIALOG=${DIALOG=dialog}

$DIALOG --title "Pirus Installation" --clear \
        --yesno "Bonjour" 10 30

case $? in
	    0) echo "oui";;
        1) echo "non";;
        255) echo "echap";;
esac
