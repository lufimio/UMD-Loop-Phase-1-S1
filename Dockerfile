FROM ubuntu:24.04

ARG ROS_DISTRO=jazzy

SHELL [ "/bin/bash", "-o", "pipefail", "-c" ]

# Install package dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  locales \
  python3 \
  python3-pip \
  python3-venv \
  software-properties-common \
  qt6-wayland \
  qtwayland5 \
  libegl1 \
  libegl-mesa0 \
  libgl1 \
  libgl1-mesa-dri \
  libglx-mesa0 \
  mesa-vulkan-drivers \
  libglu1-mesa \
  libx11-6 \
  libx11-xcb1 \
  libxcb-cursor0 \
  libxcb-glx0 \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-render-util0 \
  libxcb-shape0 \
  libxcb-xfixes0 \
  libxcb-xkb1 \
  libxext6 \
  libxrandr2 \
  libwayland-client0 \
  x11-xserver-utils \
  xauth && \
  apt-get clean

# System locale
# Important for UTF-8
RUN locale-gen en_US.UTF-8 && \
  update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
RUN mkdir -p /tmp/runtime-root && chmod 0700 /tmp/runtime-root

RUN add-apt-repository universe

RUN export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | \
  grep -F "tag_name" | awk -F'"' '{print $4}') && \
  curl -L -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(\
  . /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}}\
  )_all.deb" && \
  dpkg -i /tmp/ros2-apt-source.deb

RUN apt-get -y update && \
  apt-get upgrade -y && \
  apt-get -y install \
  python3-colcon-common-extensions \
  python3-colcon-mixin \
  python3-rosdep \
  python3-vcstool \
  ros-${ROS_DISTRO}-desktop \
  ros-${ROS_DISTRO}-ros-gz \
  ros-${ROS_DISTRO}-joint-state-publisher \
  ros-${ROS_DISTRO}-tf-transformations

RUN rosdep init && \
  rosdep update --rosdistro $ROS_DISTRO

RUN colcon mixin add default \
  https://raw.githubusercontent.com/colcon/colcon-mixin-repository/master/index.yaml && \
  colcon mixin update && \
  colcon metadata add default \
  https://raw.githubusercontent.com/colcon/colcon-metadata-repository/master/index.yaml && \
  colcon metadata update

RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc && \
  echo "export QT_QPA_PLATFORM=xcb" >> ~/.bashrc && \
  echo "unset WAYLAND_DISPLAY" >> ~/.bashrc

COPY ./startup.bash /root/simulation/startup.bash
COPY ./src /root/simulation/src

WORKDIR /root/simulation/
RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
  rosdep install -i --from-path src --rosdistro ${ROS_DISTRO} -y && \
  colcon build

RUN echo "source /root/simulation/install/setup.bash" >> ~/.bashrc

CMD [ "bash", "-lic", "ros2 launch autonomous_robot gazebo_model.launch.py"]
