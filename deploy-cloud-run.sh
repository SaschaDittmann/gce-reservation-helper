#!/bin/bash
if [ ! -f .env ]
then
  echo "Please create a .env file with the following variables:"
  exit 1
else
  export $(cat .env | xargs)
fi

gcloud run deploy ${SERVICE_NAME}-`tr -dc a-z0-9 </dev/urandom | head -c 8; echo` \
  --platform=managed --region=$REGION --project=$PROJECT_ID \
  --image=gcr.io/$PROJECT_ID/gce-reservation-helper \
  --min-instances=1 --max-instances=1 \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,ZONE=$ZONE,RESERVATION_ID=$RESERVATION_ID,MACHINE_TYPE=$MACHINE_TYPE,TARGET_VM_COUNT=$TARGET_VM_COUNT" \
  --service-account="$SERVICE_ACCOUNT" \
  --allow-unauthenticated
