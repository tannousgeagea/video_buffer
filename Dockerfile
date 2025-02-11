FROM ubuntu:22.04

LABEL maintainer="tannous.geagea@wasteant.com"
LABEL com.wasteant.version="1.1b1"

ARG user=appuser
ARG userid=1000
ARG group=appuser
ARG groupid=1000

ENV ROS_DISTRO=humble

# Install other necessary packages and dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -q -y --no-install-recommends \
    apt-utils \
	vim \
	git \
	iputils-ping \
	net-tools \
	netcat \
	ssh \
    curl \
    lsb-release \
    wget \
    zip \
    sudo \
    && rm -rf /var/lib/apt/lists/*


# Install minimal packages for ros install
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -q -y --no-install-recommends \
    curl \
    gnupg2 \
    build-essential \
    lsb-release \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*



RUN add-apt-repository universe

# add the ROS 2 GPG key with apt
RUN curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# add the repository to your sources list
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install dependencies to build your own ROS packages
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -q -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    python3 \
    python3-pip \
    python3-rosdep \
	python3-wstool\
	python3-distutils \
	python3-psutil \
    python3-tk \
    git \
	ffmpeg \
	&& rm -rf /var/lib/apt/lists/*

# Install ROS 2 packages
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -q -y --no-install-recommends \
    ros-${ROS_DISTRO}-desktop \
    ros-${ROS_DISTRO}-ros-base \
    ros-${ROS_DISTRO}-cv-bridge \
    ros-${ROS_DISTRO}-rclpy \
    ros-${ROS_DISTRO}-cv-bridge \
    ros-${ROS_DISTRO}-sensor-msgs \
    ros-dev-tools \
    && rm -rf /var/lib/apt/lists/*

# Install ROS 2 build tools and dependencies
RUN apt-get install -y \
    python3-colcon-common-extensions \
    python3-vcstool \
    git \
    && rm -rf /var/lib/apt/lists/*


RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -q -y --no-install-recommends \
    apt-utils \
    vim \
    git \
    iputils-ping \
    net-tools \
    netcat \
    ssh \
    curl \
    lsb-release \
    wget \
    zip \
    sudo \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# install python packages
RUN pip3 install supervisor
RUN pip3 install fastapi[standard]
RUN pip3 install uvicorn[standard]
RUN pip3 install gunicorn
RUN pip3 install django==4.2
RUN pip3 install asgi_correlation_id
RUN pip3 install redis
RUN pip3 install python-redis-lock
RUN pip3 install celery
RUN pip3 install flower
RUN pip3 install requests
RUN pip3 install grpcio
RUN pip3 install grpcio-tools
RUN pip3 install opencv-python
RUN pip3 install pillow
RUN pip3 install tqdm
RUN pip3 install psycopg2-binary
RUN pip3 install django-unfold

# upgrade everything
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get upgrade -q -y \
   && rm -rf /var/lib/apt/lists/*

# # Set up users and groups
RUN addgroup --gid $groupid $group && \
	adduser --uid $userid --gid $groupid --disabled-password --gecos '' --shell /bin/bash $user && \
	echo "$user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$user && \
	chmod 0440 /etc/sudoers.d/$user

RUN mkdir -p /home/$user/src
RUN mkdir -p /media/$user/media_manager

# Source the ROS 2 environment
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc

# Create directory for Supervisor logs
RUN mkdir -p /var/log/supervisor && \
    chmod -R 755 /var/log/supervisor
	

COPY . /home/${user}/src
RUN /bin/bash -c "chown -R $user:$user /home/$user/"
RUN /bin/bash -c "chown -R $user:$user /media/$user/"

COPY ./supervisord.conf /etc/supervisord.conf
COPY ./entrypoint.sh /home/.
RUN /bin/bash -c "chown $user:$user /home/entrypoint.sh"

ENTRYPOINT /bin/bash -c ". /home/entrypoint.sh"
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD /bin/sh -c "supervisorctl status || exit 1"