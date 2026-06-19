import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


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

    return os.path.join(get_package_share_directory(package_name), relative_path)


def _resolve_config_paths(value):
    if isinstance(value, dict):
        return {
            key: _resolve_config_paths(config_value)
            for key, config_value in value.items()
        }
    if isinstance(value, list):
        return [_resolve_config_paths(item) for item in value]
    return _resolve_path(value)


def _livox_node(sensor_config):
    remappings = list(sensor_config.get('remappings', {}).items())
    parameters = {
        'user_config_path': sensor_config['user_config_path'],
        'xfer_format': sensor_config.get('xfer_format', 0),
        'multi_topic': sensor_config.get('multi_topic', 0),
        'data_src': sensor_config.get('data_src', 0),
        'publish_freq': sensor_config.get('publish_freq', 10.0),
        'output_type': sensor_config.get('output_type', 0),
        'frame_id': sensor_config['frame_id'],
    }

    return Node(
        package='livox_ros_driver2',
        executable='livox_ros_driver2_node',
        name=sensor_config['node_name'],
        output='screen',
        parameters=[parameters],
        remappings=remappings,
    )


def _include_launch(package_name, launch_file, launch_arguments=None):
    launch_path = os.path.join(
        get_package_share_directory(package_name),
        'launch',
        launch_file,
    )
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(launch_path),
        launch_arguments=(launch_arguments or {}).items(),
    )


def _launch_setup(context, *args, **kwargs):
    config_file = LaunchConfiguration('config_file').perform(context)
    mode = LaunchConfiguration('mode').perform(context)
    start_front_driver = _as_bool(
        LaunchConfiguration('start_front_driver').perform(context)
    )
    start_back_driver_arg = LaunchConfiguration(
        'start_back_driver'
    ).perform(context)
    start_behavior_tree = _as_bool(
        LaunchConfiguration('start_behavior_tree').perform(context)
    )

    with open(config_file, 'r', encoding='utf-8') as file:
        config = _resolve_config_paths(yaml.safe_load(file))

    actions = []
    livox_config = config['livox']
    slam_config = config['slam']
    navigation_config = config['navigation']
    behavior_tree_config = config['behavior_tree']

    if start_front_driver:
        actions.append(_livox_node(livox_config['front']))

    start_back_driver = (
        _as_bool(start_back_driver_arg)
        if start_back_driver_arg != 'auto'
        else mode == 'navigation'
    )
    if start_back_driver:
        actions.append(_livox_node(livox_config['back']))

    if mode == 'mapping':
        actions.append(
            _include_launch(
                slam_config['package'],
                slam_config['mapping_launch'],
                {
                    'mapping_params_file': slam_config['mapping_params_file'],
                },
            )
        )

    if mode in ('relocalization', 'navigation'):
        actions.append(
            _include_launch(
                slam_config['package'],
                slam_config['relocalization_launch'],
                {
                    'relocalization_params_file':
                        slam_config['relocalization_params_file'],
                },
            )
        )

    if mode == 'navigation':
        actions.append(
            _include_launch(
                navigation_config['package'],
                navigation_config['launch_file'],
                {
                    'use_sim_time': str(
                        navigation_config.get('use_sim_time', False)
                    ).lower(),
                    'map_params_file': navigation_config['map_params_file'],
                    'params_file': navigation_config['params_file'],
                },
            )
        )

    if start_behavior_tree and mode == 'navigation':
        actions.append(
            Node(
                package=behavior_tree_config['package'],
                executable=behavior_tree_config['executable'],
                name=behavior_tree_config.get(
                    'node_name',
                    behavior_tree_config['executable'],
                ),
                output='screen',
                parameters=[
                    behavior_tree_config['params_file'],
                    {'cod_bt_path': behavior_tree_config['cod_bt_path']},
                ],
            )
        )

    return actions


def generate_launch_description():
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
            'mode',
            default_value='navigation',
            choices=['mapping', 'relocalization', 'navigation', 'drivers'],
            description='Bringup mode to launch.',
        ),
        DeclareLaunchArgument(
            'start_front_driver',
            default_value='true',
            description='Start the front MID360 Livox driver.',
        ),
        DeclareLaunchArgument(
            'start_back_driver',
            default_value='auto',
            description=(
                'Start the back MID360 Livox driver: true, false, or auto.'
            ),
        ),
        DeclareLaunchArgument(
            'start_behavior_tree',
            default_value='true',
            description='Start cod_behavior tree_1 in navigation mode.',
        ),
        OpaqueFunction(function=_launch_setup),
    ])
