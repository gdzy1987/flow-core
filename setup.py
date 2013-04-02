from setuptools import setup, find_packages

entry_points = '''
[console_scripts]
flow = flow.commands.base:main

[flow.commands]
set-token = flow.commands.set_token:SetTokenCommand
orchestrator = flow.commands.service:ServiceCommand
local_command_line_service = flow.commands.service:ServiceCommand
lsf_command_line_service = flow.commands.service:ServiceCommand
lsf_post_exec = flow.commands.lsf_post_exec:LsfPostExecCommand
command_line_wrapper = flow.commands.wrapper:WrapperCommand
configure_rabbitmq = flow.commands.configurerabbitmq:ConfigureRabbitMQCommand
console = flow.commands.console:ConsoleCommand
graph = flow.commands.graph:GraphCommand
'''

setup(
        name = 'flow',
        version = '0.1',
        packages = find_packages(exclude=[
            'unit_tests',
            'integration_tests',
            'system_tests',
            'test_helpers'
        ]),
        entry_points = entry_points,
        install_requires = [
            'blist',
            'hiredis',
            'ipython',
            'pika',
            'platform-python-lsf-api',
            'pygraphviz',
            'pyyaml',
            'redis',
            'statsd-client',
            'twisted',
        ],
        setup_requires = [
            'nose',
        ],
        tests_require = [
            'mock',
            'nose',
            'coverage',
            'fakeredis',
        ],
        test_suite = 'unit_tests',
)
