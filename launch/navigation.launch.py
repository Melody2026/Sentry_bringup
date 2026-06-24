"""Launch relocalization, Nav2, and the behavior tree."""

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


def _as_bool(value):
    return str(value).lower() in ('1', 'true', 'yes', 'on')


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
    start_behavior_tree = _as_bool(
        LaunchConfiguration('start_behavior_tree').perform(context)
    )

    with open(config_file, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)

    actions = []
    navigation_config = config['navigation']
    behavior_tree_config = config['behavior_tree']

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
                    navigation_config['map_params_file']
                ),
                'params_file': _resolve_path(
                    navigation_config['params_file']
                ),
            }.items(),
        )
    )

    if start_behavior_tree:
        actions.append(
            Node(
                package=behavior_tree_config['package'],
                executable=behavior_tree_config['executable'],
                name=behavior_tree_config.get(
                    'node_name', behavior_tree_config['executable']
                ),
                output='screen',
                parameters=[
                    _resolve_path(
                        behavior_tree_config['params_files'][color]
                    ),
                    {
                        'cod_bt_path': _resolve_path(
                            behavior_tree_config['cod_bt_path']
                        )
                    },
                ],
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
        DeclareLaunchArgument(
            'start_behavior_tree',
            default_value='true',
            description='Start cod_behavior tree_1.',
        ),
        OpaqueFunction(function=_launch_setup),
    ])
