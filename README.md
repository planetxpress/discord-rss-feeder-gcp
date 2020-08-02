# Discord RSS GCP bot
Posting RSS updates to Discord executed by GCP Functions.

GCP object storage is used to save state between function runs.

### Requirements
- A preconfigured a GCP Secret containing your Discord webhook URL.
- Set environment variables
  - `TIMESTAMP_BUCKET` - Name of your bucket. This must be unique among all GCP.
  - `TIMESTAMP_OBJECT` - Name this file anything you want.
  - `WEBHOOK_KEY` - Name of the preconfigured secret key containing your webhook URL
