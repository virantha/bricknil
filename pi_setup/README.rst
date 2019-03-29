Setting up a Raspberry Pi with Python 3.7+ using Ansible
########################################################

Here's a set of files to automatically setup bricknil_ on a Raspberry Pi.
These Ansible_ playbooks will help you take a clean Raspbian image and compile
Python 3.7+ along with all the Bricknil required libraries.  You just need a
Raspberry Pi; these instructions do not require you to plug in a monitor and
works over Wifi.  This compilation of Python is necessary because the raspbian distro
does not ship with the latest version of Python at the time of this writing.  And it
took me a little bit of effort to figure out how to compile Python with the SSL libraries (so pip works), 
so I hope this might be of use to some folks.  

The steps required are listed below in order, and you can find the Ansible yaml playbooks
in the Bricknil source under `pi_setup <https://github.com/virantha/bricknil/tree/master/bricknil/pi_setup/>`_.

.. _bricknil: https://virantha.github.io/bricknil
.. _Ansible: https://www.ansible.com/resources/get-started

Steps
============

Download a Raspbian image and burn it to a SD card
--------------------------------------------------
#. Download the `Raspbian Stretch Lite <https://www.raspberrypi.org/downloads/raspbian/>`_ image
#. Burn it to a suitable SD card.  On OS X, `Balena Etcher <https://www.balena.io/etcher/>`_ is a good tool to do this.
#. On the newly imaged SD card's `/boot` folder:

   #. Make an empty file called `ssh` to enable SSH access.
   #. Make `wpa_supplicant.conf` file to supply your wifi credentials::

         country=US
         ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
         update_config=1

         network={
               ssid="NETWORK_NAME
               psk="WIFI PASSWORD"
         }

#. Now, you should be able to use this SD card to boot your raspberry pi. After giving it a few minutes to boot, you can login in by doing the following on your local machine::

      ssh pi@raspberrypi.local
      <enter 'raspberry' as the default password

Install Ansbile on your local machine
-------------------------------------
You can just type `pip install ansible`

Change the default password on the Pi
-------------------------------------
#. You may need to modify the `hosts` file in `pi_setup` directory to put in your own IP address for the Pi.
#. You will need to install the python library `passlib` by running `pip install passlib` on your local machine (not the Pi)
#. Use the `change_password.yml` playbook to test your ansible install and change the default password on the pi (use `raspberry` for the
   ssh password when prompted, and then enter your new password)::

      ansible-playbook -i hosts change_password.yml --ask-pass
   
   The playbook being run is simply:

.. literalinclude:: ../pi_setup/change_password.yml
    :language: yaml

Run the setup playbook
----------------------
#. The final step is to just run the the install playbook.  This will install all the packages, download Python 3.7, compile it, and set up
   a virtualenv to run bricknil from.   The actual playbook is in `tasks.yml`, shown below and included in the source, and the command to 
   execute it on your local machine is::

      ansible-playbook -i hosts tasks.yml --ask-pass

   The install will take around two hours, so please be patient.  Most of the time is spent compiling and installing Python from source. 
   Here's the playbook being executed:

   .. literalinclude:: ../pi_setup/tasks.yml
       :language: yaml

#. And that's it! Your raspberry pi should be ready to go as a networked appliance to run your Lego controller scripts from.

Running Bricknil examples on the Pi
-----------------------------------
#. The script installs a virtualenv called `bricknil`, so you can activate it in the normal way to get access to Python 3.7+ and the python
   dependencies for running bricknil.

#. The script also installed the bricknil_ source from github, so all the examples should be ready to go.  Just ssh into the Pi and::

      cd bricknil
  
#. On linux,  you need to run as sudo to 
   access the bluetooth libraries; after you login to the Pi over ssh  you can do the following to run the virtualenv installed Python as sudo::

      sudo ~/.virtualenvs/bricknil/bin/python examples/train_all.py


