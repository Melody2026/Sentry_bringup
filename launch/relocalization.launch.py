"""Launch the dual Livox driver, republisher, and SLAM relocalization."""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node

import yaml


def _resolve_path(value):
    if not isinstance(value, str):
        return value

    value = os.path.expanduser(value)
    if not value.startswith('package://'):
        return value

    package_path = value[len('package://'):]
    package_name, separator, relative_path = package_path.partition('/')
    if not separator:
        return get_package_share_directory(package_name)
    return os.path.join(
        get_package_share_directory(package_name), relative_path
    )


def _launch_setup(context):
    config_file = LaunchConfiguration('config_file').perform(context)
    color = LaunchConfiguration('color').perform(context)

    with open(config_file, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)

    actions = []
    dual_config = config['livox']['dual']
    slam_config = config['slam']

    actions.extend([
        Node(
            package='livox_ros_driver2',
            executable='livox_ros_driver2_node',
            name=dual_config['node_name'],
            output='screen',
            parameters=[{
                'user_config_path': _resolve_path(
                    dual_config['user_config_path']
                ),
                'xfer_format': dual_config.get('xfer_format', 0),
                'multi_topic': dual_config.get('multi_topic', 1),
                'data_src': dual_config.get('data_src', 0),
                'publish_freq': dual_config.get('publish_freq', 10.0),
                'output_type': dual_config.get('output_type', 0),
                'frame_id': dual_config['frame_id'],
            }],
        ),
        Node(
            package='cpp_lidar_filter',
            executable='dual_lidar_republisher',
            name='dual_lidar_republisher',
            output='screen',
        ),
    ])

    relocalization_launch = os.path.join(
        get_package_share_directory(slam_config['package']),
        'launch',
        slam_config['relocalization_launch'],
    )
    actions.append(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(relocalization_launch),
            launch_arguments={
                'relocalization_params_file': _resolve_path(
                    slam_config['relocalization_params_files'][color]
                ),
            }.items(),
        )
    )
    return actions


def generate_launch_description():
    """Generate the relocalization launch description."""
    default_config_file = os.path.join(
        get_package_share_directory('sentry_bringup'),
        'config',
        'sentry_bringup.yaml',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'config_file',
            default_value=default_config_file,
            description='Path to the sentry bringup yaml config.',
        ),
        DeclareLaunchArgument(
            'color',
            default_value='red',
            choices=['red', 'blue'],
            description='Team color used to select relocalization config.',
        ),
        OpaqueFunction(function=_launch_setup),
    ])
