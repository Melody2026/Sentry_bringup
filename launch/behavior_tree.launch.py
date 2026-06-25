"""Launch the behavior tree."""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import OpaqueFunction
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

    behavior_tree_config = config['behavior_tree']

    return [
        Node(
            package=behavior_tree_config['package'],
            executable=behavior_tree_config['executable'],
            name=behavior_tree_config.get(
                'node_name', behavior_tree_config['executable']
            ),
            output='screen',
            parameters=[
                _resolve_path(behavior_tree_config['params_files'][color]),
                {
                    'cod_bt_path': _resolve_path(
                        behavior_tree_config['cod_bt_path']
                    )
                },
            ],
        )
    ]


def generate_launch_description():
    """Generate the behavior tree launch description."""
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
            description='Team color used to select behavior tree config.',
        ),
        OpaqueFunction(function=_launch_setup),
    ])
