"""Launch relocalization and Nav2."""

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
    navigation_config = config['navigation']

    relocalization_launch = os.path.join(
        get_package_share_directory('sentry_bringup'),
        'launch',
        'relocalization.launch.py',
    )
    actions.append(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(relocalization_launch),
            launch_arguments={
                'config_file': config_file,
                'color': color,
            }.items(),
        )
    )

    navigation_launch = os.path.join(
        get_package_share_directory(navigation_config['package']),
        'launch',
        navigation_config['launch_file'],
    )
    actions.append(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(navigation_launch),
            launch_arguments={
                'use_sim_time': 'false',
                'map_params_file': _resolve_path(
                    navigation_config['map_params_files'][color]
                ),
                'params_file': _resolve_path(
                    navigation_config['params_file']
                ),
            }.items(),
        )
    )
    actions.append(
        Node(
            package='cod_behavior',
            executable='log_recorder',
            name='log_recorder',
            output='screen',
        )
    )

    return actions


def generate_launch_description():
    """Generate the navigation launch description."""
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
            description='Team color used to select runtime configs.',
        ),
        OpaqueFunction(function=_launch_setup),
    ])
