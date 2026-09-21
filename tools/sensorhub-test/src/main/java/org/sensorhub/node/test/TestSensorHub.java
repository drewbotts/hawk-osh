package org.sensorhub.node.test;

import org.sensorhub.impl.SensorHub;


public class TestSensorHub
{
    private TestSensorHub()
    {
    }

    public static void main(String[] args) throws Exception
    {
        SensorHub.main(new String[] {"tools/sensorhub-test/src/main/resources/config.json", "storage"});
    }
}
