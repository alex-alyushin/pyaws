#!/usr/bin/env python3

import boto3
import argparse
import subprocess

from datetime import datetime


def describe_instance(requested_name, region_name=None):
    ec2_client = boto3.client('ec2', region_name=region_name)
    response = ec2_client.describe_instances(
        Filters=[
            {
                "Name": "tag:Name",
                "Values": [requested_name]
            }
        ]
    )

    assert len(response['Reservations']) > 0, f"Instance \"{requested_name}\" is not found"
    assert len(response['Reservations']) == 1, f"Instance \"{requested_name}\" must be uniq"

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_name = { item['Key'] : item['Value'] for item in instance['Tags'] }.get('Name')

            print(f"Found instance: {instance_name} id={instance_id}")
            assert instance_name == requested_name, f"Found={instance_name} and arg={requested_name} must be equal"

            state = instance.get('State', {}).get('Name')
            print(f"\tState: {state}")

            instance_ip = instance.get('PublicIpAddress')
            print(f"\tIP: {instance_ip}\n")

    return {
        'id': instance_id,
        'name': instance_name,
        'ip': instance_ip,
    }


def start_instance(instance_id, region_name=None):
    ec2_client = boto3.client('ec2', region_name=region_name)
    ec2_client.start_instances(InstanceIds=[instance_id])

    time = datetime.now().time().replace(microsecond=0)
    print(f"[{time}] Instance id={instance_id} waiting until running ...")

    ec2_resource = boto3.resource('ec2', region_name=region_name)
    instance = ec2_resource.Instance(instance_id)
    instance.wait_until_running()

    time = datetime.now().time().replace(microsecond=0)
    print(f"[{time}] Instance id={instance_id} successfully started!")


def ssh_connect(instance_name, instance_ip, tmux_session=None):
    time = datetime.now().time().replace(microsecond=0)
    print(f"[{time}] ssh connect {instance_ip} ...")

    cmd = [
        "ssh",
        "-t",
        instance_name,
        "-o", f"HostName={instance_ip}",
        "-o", f"User=ubuntu",
    ]

    if tmux_session is not None:
        if tmux_session == 'new':
            cmd.append(f"tmux new -s se_{time.hour}_{time.minute}")
        else:
            cmd.append(f"tmux attach -t {tmux_session}")

    subprocess.run(cmd, check=True)


def parse_comand_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--name')
    parser.add_argument('--region')
    parser.add_argument('--tmux')

    return parser.parse_args()


args = parse_comand_args()

instance_before = describe_instance(args.name, args.region)
start_instance(instance_before['id'], args.region)

instance_after = describe_instance(args.name, args.region)
ssh_connect(instance_after['name'], instance_after['ip'], args.tmux)
