#!/bin/bash

set -e

echo "=== Setting up RabbitMQ queues ==="

# Use environment variables from RabbitMQ container
USER=${RABBITMQ_DEFAULT_USER}
PASS=${RABBITMQ_DEFAULT_PASS}
HOST=${RABBITMQ_HOST}
PORT=${RABBITMQ_MANAGEMENT_POR}

# Wait for RabbitMQ to be ready
echo "Waiting for RabbitMQ to be ready..."
if rabbitmq-diagnostics -q ping > /dev/null 2>&1; then
  echo "RabbitMQ is ready!"
else
  cho "Attempt $i/30: RabbitMQ not ready yet..."
  exit 1
fi

# Wait a bit more for management plugin
echo "Waiting for management plugin to load..."
sleep 5

# Set credentials for rabbitmqadmin (using environment variables)
export RABBITMQ_USERNAME=$USER
export RABBITMQ_PASSWORD=$PASS

# Create exchange
echo "Creating exchange 'price_changes'..."
rabbitmqadmin declare exchange name=price_changes type=direct durable=true

# Create queues
echo "Creating queues..."
rabbitmqadmin declare queue name=commands durable=true
rabbitmqadmin declare queue name=price_change_level_1 durable=true
rabbitmqadmin declare queue name=price_change_level_2 durable=true
rabbitmqadmin declare queue name=price_change_level_3 durable=true

# Bind queues to exchange
echo "Binding queues to exchange..."
rabbitmqadmin declare binding source=price_changes destination_type=queue destination=price_change_level_1 routing_key=level_1
rabbitmqadmin declare binding source=price_changes destination_type=queue destination=price_change_level_2 routing_key=level_2
rabbitmqadmin declare binding source=price_changes destination_type=queue destination=price_change_level_3 routing_key=level_3
rabbitmqadmin declare binding source=price_changes destination_type=queue destination=commands routing_key=commands

# List created queues and bindings
echo ""
echo "=== Created queues ==="
rabbitmqadmin list queues name durable

echo ""
echo "=== Created bindings ==="
rabbitmqadmin list bindings source destination routing_key

echo ""
echo "✅ RabbitMQ setup completed successfully!"