from ament_index_python.packages import get_package_share_directory
import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    robotXacroName = "differential_drive_robot"
    namePackage = "autonomous_robot"
    modelFileRelativePath = "model/robot.xacro"
    pathModelFile = os.path.join(
        get_package_share_directory(namePackage), modelFileRelativePath
    )
    robotDescription = xacro.process_file(pathModelFile).toxml()

    gazbo_rosPackageLaunch = PythonLaunchDescriptionSource(
        os.path.join(
            get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py"
        )
    )
    gazebo_launch = IncludeLaunchDescription(
        gazbo_rosPackageLaunch,
        launch_arguments={
            "gz_args": "-r -v -v4 empty.sdf",
            "on_exit_shutdown": "true",
        }.items(),
    )

    spawnModelNodeGazebo = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-name", robotXacroName, "-topic", "robot_description"],
        output="screen",
    )

    nodeRobotStatePublisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robotDescription, "use_sim_time": True}],
        output="screen",
    )

    bridge_params = os.path.join(
        get_package_share_directory(namePackage), "parameters", "bridge_parameters.yaml"
    )

    start_gazebo_ros_bridge_cmd = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["--ros-args", "-p", f"config_file:={bridge_params}"],
        output="screen",
    )

    launchDescriptionObject = LaunchDescription()
    launchDescriptionObject.add_action(gazebo_launch)
    launchDescriptionObject.add_action(spawnModelNodeGazebo)
    launchDescriptionObject.add_action(nodeRobotStatePublisher)
    launchDescriptionObject.add_action(start_gazebo_ros_bridge_cmd)

    return launchDescriptionObject
