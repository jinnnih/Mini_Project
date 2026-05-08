import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node


def generate_launch_description():
    world_file = os.path.join(
        os.path.expanduser('~'),
        'ros2_ws', 'src', 'parking_vision',
        'simulation', 'worlds', 'carwash.world'
    )

    return LaunchDescription([

        # Gazebo 실행
        ExecuteProcess(
            cmd=['gz', 'sim', world_file, '-r'],
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