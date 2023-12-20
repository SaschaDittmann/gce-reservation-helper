#!/bin/bash
if [ ! -f .env ]
then
  echo "Please create a .env file with the following variables:"
  exit 1
else
  export $(cat .env | xargs)
fi

docker build -t gce-reservation-helper .
docker tag gce-reservation-helper gcr.io/$PROJECT_ID/gce-reservation-helper
docker push gcr.io/$PROJECT_ID/gce-reservation-helper
