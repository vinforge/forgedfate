#!/bin/bash

# Docker entrypoint script for Kismet export client
# Reads configuration from environment variables

set -e

# Default values
KISMET_HOST=${KISMET_HOST:-localhost}
KISMET_PORT=${KISMET_PORT:-2501}
UPDATE_RATE=${UPDATE_RATE:-5}
EXPORT_TYPE=${EXPORT_TYPE:-console}

# Build command line arguments
ARGS="--kismet-host $KISMET_HOST --kismet-port $KISMET_PORT --update-rate $UPDATE_RATE --export-type $EXPORT_TYPE"

# Add database-specific arguments based on export type
case $EXPORT_TYPE in
    postgres)
        if [ -z "$POSTGRES_CONN" ]; then
            echo "Error: POSTGRES_CONN environment variable required for PostgreSQL export"
            exit 1
        fi
        ARGS="$ARGS --postgres-conn $POSTGRES_CONN"
        ;;
    influxdb)
        if [ -z "$INFLUX_URL" ] || [ -z "$INFLUX_TOKEN" ] || [ -z "$INFLUX_ORG" ] || [ -z "$INFLUX_BUCKET" ]; then
            echo "Error: INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, and INFLUX_BUCKET environment variables required for InfluxDB export"
            exit 1
        fi
        ARGS="$ARGS --influx-url $INFLUX_URL --influx-token $INFLUX_TOKEN --influx-org $INFLUX_ORG --influx-bucket $INFLUX_BUCKET"
        ;;
    mqtt)
        if [ -z "$MQTT_HOST" ]; then
            echo "Error: MQTT_HOST environment variable required for MQTT export"
            exit 1
        fi
        ARGS="$ARGS --mqtt-host $MQTT_HOST"
        
        # Optional MQTT parameters
        [ ! -z "$MQTT_PORT" ] && ARGS="$ARGS --mqtt-port $MQTT_PORT"
        [ ! -z "$MQTT_TOPIC_PREFIX" ] && ARGS="$ARGS --mqtt-topic-prefix $MQTT_TOPIC_PREFIX"
        [ ! -z "$MQTT_USERNAME" ] && ARGS="$ARGS --mqtt-username $MQTT_USERNAME"
        [ ! -z "$MQTT_PASSWORD" ] && ARGS="$ARGS --mqtt-password $MQTT_PASSWORD"
        ;;
    console)
        # No additional arguments needed for console output
        ;;
    *)
        echo "Error: Unknown export type: $EXPORT_TYPE"
        echo "Supported types: console, postgres, influxdb, mqtt"
        exit 1
        ;;
esac

echo "Starting Kismet export client with: $ARGS"
echo "Export type: $EXPORT_TYPE"
echo "Kismet server: $KISMET_HOST:$KISMET_PORT"
echo "Update rate: ${UPDATE_RATE}s"

# Wait for Kismet server to be available
echo "Waiting for Kismet server to be available..."
while ! nc -z $KISMET_HOST $KISMET_PORT; do
    echo "Kismet server not ready, waiting 5 seconds..."
    sleep 5
done

echo "Kismet server is available, starting export client..."

# Execute the Python script with constructed arguments
exec python3 kismet_realtime_export.py $ARGS
