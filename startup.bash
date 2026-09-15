#!/bin/bash

source /opt/ros/jazzy/setup.bash
source ./install/setup.bash
ros2 launch autonomous_robot gazebo_model.launch.py &
ros2 run autonomous_robot publisher
