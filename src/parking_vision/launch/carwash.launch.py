import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    world_file = os.path.join(
        get_package_share_directory('parking_vision'),
        'simulation', 'worlds', 'carwash.world'
    )

    return LaunchDescription([

        # Gazebo Sim 8 실행
        ExecuteProcess(
            cmd=['gz', 'sim', world_file, '-r'],
            output='screen'
        ),

        # Gazebo ↔ ROS2 브릿지 (카메라: gz→ros, cmd_vel: ros→gz)
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
                '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            ],
            output='screen'
        ),

        # Vision Node
        Node(
            package='parking_vision',
            executable='vision_node',
            name='vision_node',
            output='screen'
        ),

        # Control Node
        Node(
            package='parking_vision',
            executable='control_node',
            name='control_node',
            output='screen'
        ),

    ])
