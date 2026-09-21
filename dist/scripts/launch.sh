#!/bin/bash

# Run from the node's install folder so relative paths resolve no matter where this is called from
# (e.g. a systemd unit).
cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" || exit 1

# Start the node
java -Xmx512m \
	-Dlogback.configurationFile=./config/logback.xml \
	-cp "lib/*:userclasses:userlib/*" \
	-Djava.system.class.loader="org.sensorhub.utils.NativeClassLoader" \
	org.sensorhub.impl.SensorHub ./config/config.json ./db
