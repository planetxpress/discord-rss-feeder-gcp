import feedparser
import json
import logging
import os
import requests
import time
from google.cloud import exceptions
from google.cloud import storage
from google.cloud import secretmanager
storage_client = storage.Client()
secret_client = secretmanager.SecretManagerServiceClient()

TIMESTAMP_FORMAT = '%d-%m-%Y %H:%M'


def check_environment():
    required = [
        'RSS_FEED',
        'TIMESTAMP_BUCKET',
        'TIMESTAMP_OBJECT',
        'WEBHOOK_KEY'
    ]
    fail = False
    for var in required:
        if not os.getenv(var):
            fail = True
            logging.error('Missing environment variable %s' % var)
    if fail:
        exit(1)


def upload_timestamp(timestamp):
    timestamp_string = time.strftime(TIMESTAMP_FORMAT, timestamp)
    try:
        bucket = storage_client.bucket(os.getenv('TIMESTAMP_BUCKET'))
        blob = bucket.blob(os.getenv('TIMESTAMP_OBJECT'))
        blob.upload_from_string(timestamp_string, content_type='text/plain')
    except exceptions.NotFound:
        bucket = storage_client.create_bucket(os.getenv('TIMESTAMP_BUCKET'))
        blob = bucket.blob(os.getenv('TIMESTAMP_OBJECT'))
        blob.upload_from_string(timestamp_string, content_type='text/plain')
    except exceptions.Forbidden:
        logging.error(
            'You do not have permission to this bucket. ' \
            'Someone else may have already taken this bucket name or your permissions are wrong.'
        )
        exit(1)
    except Exception as ex:
        logging.error('GCP Storage error: %s' % ex)
        exit(1)


def download_timestamp():
    bucket = storage_client.bucket(os.getenv('TIMESTAMP_BUCKET'))
    blob = bucket.blob(os.getenv('TIMESTAMP_OBJECT'))
    try:
        timestamp_string = blob.download_as_string().decode('utf-8').strip()
        timestamp = time.strptime(timestamp_string, TIMESTAMP_FORMAT)
    except exceptions.NotFound:
        logging.warning('No previous timestamp. Gathering all available entries since 1970.')
        timestamp = time.gmtime(0)
    except exceptions.Forbidden:
        logging.error(
            'You do not have permission to this bucket. ' \
            'Someone else may have already taken this bucket name or your permissions are wrong.'
        )
        exit(1)
    except Exception as ex:
        logging.error(ex)
        exit(1)
    return timestamp


def discord_post(content):
    message = {
        'content': content
    }
    secret_path = secret_client.secret_version_path(
        os.getenv('GOOGLE_CLOUD_PROJECT'), os.getenv('WEBHOOK_KEY'), 'latest'
    )
    try:
        webhook = secret_client.access_secret_version(secret_path).payload.data.decode('utf-8')
        requests.post(webhook, data=message)
    except Exception as ex:
        logging.error('Error getting/posting Discord webhook: %s' % ex)


def main():
    check_environment()
    f = feedparser.parse(os.getenv('RSS_FEED'))
    timestamp = f.feed.updated_parsed
    previous_timestamp = download_timestamp()
    if timestamp > previous_timestamp:
        upload_timestamp(timestamp)
    for entry in reversed(f.entries):
        if entry.published_parsed > previous_timestamp:
            discord_post(entry.link)
            time.sleep(3)


def pubsub_trigger(event, context):
    main()

if __name__== '__main__':
    main()