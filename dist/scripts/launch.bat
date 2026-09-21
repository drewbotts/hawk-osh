@echo off
setlocal

REM Run from the node's install folder so relative paths resolve
cd /d %~dp0

REM Start the node
java -Xmx512m ^
    -Dlogback.configurationFile=./config/logback.xml ^
    -cp "lib/*;userclasses;userlib/*" ^
    -Djava.system.class.loader="org.sensorhub.utils.NativeClassLoader" ^
    org.sensorhub.impl.SensorHub ./config/config.json db

endlocal
