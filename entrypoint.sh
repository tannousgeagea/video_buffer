#!/bin/bash
set -e

echo "🔄 Running Django Migrations..."
/bin/bash -c "python3 /home/$user/src/video_buffer/manage.py makemigrations"
/bin/bash -c "python3 /home/$user/src/video_buffer/manage.py migrate"
/bin/bash -c "python3 /home/$user/src/video_buffer/manage.py create_superuser"

# ✅ Detect ROS2 Topics Before Starting Services
echo "🔍 Detecting ROS2 Topics..."
/bin/bash -c "source /opt/ros/$ROS_DISTRO/setup.bash"
/bin/bash -c "source /opt/ros/$ROS_DISTRO/setup.bash && python3 /home/$user/src/video_buffer/manage.py detect_ros2_topics"

echo "🚀 Starting Supervisor (Django will be available)..."
sudo -E supervisord -n -c /etc/supervisord.conf &

# Sleep for a few seconds to ensure Django starts properly
echo "⏳ Waiting for Django to initialize..."
sleep 5

# 🚨 Wait for configuration before starting other services
echo "🚨 Waiting for app configuration before launching other services..."
until /bin/bash -c "python3 /home/$user/src/video_buffer/manage.py check_config"; do
    echo "🔄 Configuration not found. Waiting..."
    sleep 15
done
echo "✅ App is configured! Proceeding..."

# 🚀 Start delayed services after configuration is complete
echo "🚀 Starting Core Services..."
/bin/bash -c "supervisorctl start all"
