import feedparser
import json
import logging
import os
import requests
import time
from google.cloud import storage
from google.cloud import secretmanager
storage_client = storage.Client()
secret_client = secretmanager.SecretManagerServiceClient()

TIMESTAMP_FORMAT = '%d-%m-%Y %H:%M'


def upload_timestamp(timestamp):
    timestamp_string = time.strftime(TIMESTAMP_FORMAT, timestamp)
    try:
        bucket = storage_client.bucket(os.getenv('TIMESTAMP_BUCKET'))
        blob = bucket.blob(os.getenv('TIMESTAMP_OBJECT'))
        blob.upload_from_string(timestamp_string, content_type='text/plain')
    except:
        bucket = storage_client.create_bucket(os.getenv('TIMESTAMP_BUCKET'))
        blob = bucket.blob(os.getenv('TIMESTAMP_OBJECT'))
        blob.upload_from_string(timestamp_string, content_type='text/plain')


def download_timestamp():
    bucket = storage_client.bucket(os.getenv('TIMESTAMP_BUCKET'))
    blob = bucket.blob(os.getenv('TIMESTAMP_OBJECT'))
    timestamp_string = blob.download_as_string().decode('utf-8').strip()
    timestamp = time.strptime(timestamp_string, TIMESTAMP_FORMAT)
    return timestamp


def discord_post(content):
    secret_path = secret_client.secret_version_path(
        os.getenv('GOOGLE_CLOUD_PROJECT'), os.getenv('WEBHOOK_KEY'), 'latest'
    )
    webhook = secret_client.access_secret_version(secret_path).payload.data.decode('utf-8')
    message = {
        'content': content
    }
    requests.post(webhook, data=message)


def main():
    f = feedparser.parse(os.getenv('RSS_FEED'))
    timestamp = f.feed.updated_parsed
    previous_timestamp = download_timestamp()
    for entry in reversed(f.entries):
        if entry.published_parsed > previous_timestamp:
            discord_post(entry.link)
            time.sleep(1)
    if timestamp > previous_timestamp:
        upload_timestamp(timestamp)


def pubsub_trigger(event, context):
    main()

if __name__== '__main__':
    main()