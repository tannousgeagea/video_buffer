#!/bin/bash
set -e

/bin/bash -c "python3 /home/$user/src/video_buffer/manage.py makemigrations"
/bin/bash -c "python3 /home/$user/src/video_buffer/manage.py migrate"
/bin/bash -c "python3 /home/$user/src/video_buffer/manage.py create_superuser"

/bin/bash  -c "source /opt/ros/$ROS_DISTRO/setup.bash"

sudo -E supervisord -n -c /etc/supervisord.conf