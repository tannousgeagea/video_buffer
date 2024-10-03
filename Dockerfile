FROM ros:noetic-ros-core-focal

LABEL maintainer="tannous.geagea@wasteant.com"
LABEL com.wasteant.version="1.1b1"

ENV user=appuser
ARG user=appuser
ARG userid=1000
ARG group=appuser
ARG groupid=1000

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -q -y --no-install-recommends \
    apt-utils \
    vim \
    git \
    iputils-ping \
    netcat \
    ssh \
    curl \
    lsb-release \
    wget \
    zip \
    sudo \
    cron \
    && rm -rf /var/lib/apt/lists/*

# install python dependancies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -q -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    python3 \
	python3-rosdep \
	python3-rosinstall \
	python3-rosinstall-generator \
	python3-wstool build-essential \
	python3-rosdep \
    python3-pip \
    python3-dev \
    python3-wstool \
    build-essential \
    python3-distutils \
    python3-psutil \
    python3-tk \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

#>>>note: rosdep update is not included because otherwise only root will have access to the database 
RUN rm -f /etc/ros/rosdep/sources.list.d/20-default.list && rosdep init 

RUN addgroup --gid $groupid $group \
    && adduser --uid $userid --gid $groupid --disabled-password --gecos '' --shell /bin/bash $user \
    && echo "$user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$user \
    && chmod 0440 /etc/sudoers.d/$user

RUN mkdir -p /home/$user/src
RUN mkdir -p /media

RUN /bin/bash -c ". /opt/ros/noetic/setup.bash; catkin_init_workspace /home/$user/src"  
RUN /bin/bash -c ". /opt/ros/noetic/setup.bash; cd /home/$user; catkin_make"

RUN /bin/bash -c "echo source /opt/ros/noetic/setup.bash >> /home/$user/.bashrc"
RUN /bin/bash -c "echo source /home/$user/devel/setup.bash >> /home/$user/.bashrc"

RUN /bin/bash -c "chown -R $user:$user /home/$user/"
RUN /bin/bash -c "chown -R $user:$user /media"

# Create directory for Supervisor logs
RUN mkdir -p /var/log/supervisor && \
    chmod -R 755 /var/log/supervisor

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
RUN pip3 install roslibpy
RUN pip3 install cvbridge3
RUN pip3 install opencv-python
RUN pip3 install pillow
RUN pip3 install tqdm
RUN pip3 install psycopg2-binary

COPY ./supervisord.conf /etc/supervisord.conf
COPY ./entrypoint.sh /home/
RUN /bin/bash -c "chown -R $user:$user /home/"
ENTRYPOINT /bin/bash -c ". /home/entrypoint.sh"
