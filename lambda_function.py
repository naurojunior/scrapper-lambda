"""
Lambda function to scrap information
and compare with the last status.
In case of difference, sends a message via Telegram.
"""

import configparser
import json
from datetime import datetime
import boto3
from bs4 import BeautifulSoup
import requests

config = configparser.ConfigParser()
config.read('config.ini')

company_url = config['DEFAULT']['CompanyURL']
api_token = config['DEFAULT']['APIToken']
chat_id = config['DEFAULT']['ChatId']

DEFAULT_TABLE = config['DYNAMODB']['DefaultTable']
DEFAULT_ID = config['DYNAMODB']['DefaultId']


def get_last_status(client):
    """"Returns the last status from DynamoDB of the run"""

    data = client.get_item(
        TableName=DEFAULT_TABLE,
        Key={
            'id': {
                'S': DEFAULT_ID
            }
        }
    )

    return data['Item']['last_status']['S']


def update_status(client, current_status, current_time):
    """"Updates on DynamoDB the current status of the run"""

    print("Update status")
    client.update_item(
        TableName=DEFAULT_TABLE,
        Key={
            'id': {'S': DEFAULT_ID}
        },
        UpdateExpression="SET last_status = :r, last_update = :t",
        ExpressionAttributeValues={
            ':t': {'S': current_time},
            ':r': {'S': current_status},
        }
    )


def send_message(message):
    """"Send message via Telegram"""

    print("Send Message")

    api_url = f'https://api.telegram.org/bot{api_token}/sendMessage'

    requests.post(
        api_url,
        json={
            'chat_id': chat_id,
            'text': message},
        timeout=5)


def lambda_handler(_event, _context):
    """"Lambda Handler default for AWS Lambda"""

    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    client = boto3.client('dynamodb')

    last_status = get_last_status(client)

    page = requests.get(
        company_url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/107.0.0.0 Safari/537.36'},
        timeout=5)

    print("Request made")

    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.find(id="statusModal")
    box_title = results.find("div", class_="box-titulo")
    status = box_title.find("div").find("div")["style"]

    if "#f51616" in str(status):
        current_status = "offline"
        current_message = "Interrupção no serviço"
    else:
        current_status = "online"
        current_message = "Serviço voltou a funcionar"

    if current_status != last_status:
        print("Changes found! Current status:" + current_status)
        update_status(client, current_status, current_time)
        send_message(current_message)
    else:
        print("Nothing changed. Current status:" + current_status)

    response = {'statusCode': 200,
                'body': json.dumps({'current_status': current_status,
                                    'current_time': current_time,
                                    'last_status': last_status}),
                'headers': {'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'},
                }

    return response
