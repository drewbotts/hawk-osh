#!/usr/bin/env python3
"""
JBD/Xiaoxiang BMS BLE -> MQTT bridge.

Connects to the BMS over BLE GATT, polls basic info (0x03) and cell
voltages (0x04), and publishes a merged BatteryStatus JSON document that
the OSH sensorhub-driver-jbd module consumes.

GATT layout (standard JBD):
  service FF00, write char FF02 (requests), notify char FF01 (responses).
Responses can span multiple notifications; frames are reassembled until
the trailing 0x77 byte and validated by checksum.

    pip install bleak paho-mqtt
    python3 jbd_ble_mqtt.py --mac A4:C1:38:xx:xx:xx
"""
import argparse
import asyncio
import json
import logging
import struct
import time

import paho.mqtt.client as mqtt
from bleak import BleakClient

LOG = logging.getLogger("jbd-bridge")

CHAR_NOTIFY = "0000ff01-0000-1000-8000-00805f9b34fb"
CHAR_WRITE  = "0000ff02-0000-1000-8000-00805f9b34fb"
REQ_BASIC   = bytes.fromhex("dda50300fffd77")
REQ_CELLS   = bytes.fromhex("dda50400fffc77")


def valid_frame(f: bytes) -> bool:
    if len(f) < 7 or f[0] != 0xDD or f[-1] != 0x77:
        return False
    ln = f[3]
    if len(f) != ln + 7:
        return False
    chk = struct.unpack(">H", f[4 + ln:6 + ln])[0]
    return (sum(f[2:4 + ln]) + chk) & 0xFFFF == 0


def parse_basic(f: bytes, out: dict):
    p = f[4:]
    out["ts"] = time.time()
    out["voltage"] = struct.unpack(">H", p[0:2])[0] * 0.01
    out["current"] = struct.unpack(">h", p[2:4])[0] * 0.01
    out["remainingAh"] = struct.unpack(">H", p[4:6])[0] * 0.01
    out["fullAh"] = struct.unpack(">H", p[6:8])[0] * 0.01
    out["cycles"] = struct.unpack(">H", p[8:10])[0]
    out["protection"] = struct.unpack(">H", p[16:18])[0]
    out["soc"] = p[19]
    out["chargeFet"] = bool(p[20] & 0x01)
    out["dischargeFet"] = bool(p[20] & 0x02)
    ntc = p[22]
    out["temps"] = [
        (struct.unpack(">H", p[23 + 2 * i:25 + 2 * i])[0] - 2731) / 10.0
        for i in range(ntc)
    ]


def parse_cells(f: bytes, out: dict):
    ln = f[3]
    out["cells"] = [
        struct.unpack(">H", f[4 + 2 * i:6 + 2 * i])[0] / 1000.0
        for i in range(ln // 2)
    ]


class FrameAssembler:
    def __init__(self):
        self.buf = bytearray()
        self.done = asyncio.Event()
        self.frame = None

    def feed(self, data: bytes):
        self.buf += data
        if self.buf and self.buf[-1] == 0x77:
            self.frame = bytes(self.buf)
            self.buf = bytearray()
            self.done.set()

    async def request(self, client, req: bytes, timeout=5.0) -> bytes:
        self.frame = None
        self.done.clear()
        await client.write_gatt_char(CHAR_WRITE, req, response=False)
        await asyncio.wait_for(self.done.wait(), timeout)
        return self.frame


async def run(args):
    mq = mqtt.Client(client_id="jbd-ble-bridge")
    mq.connect(args.broker, args.port)
    mq.loop_start()

    while True:
        try:
            LOG.info("connecting to %s", args.mac)
            async with BleakClient(args.mac, timeout=20.0) as client:
                asm = FrameAssembler()
                await client.start_notify(CHAR_NOTIFY, lambda _, d: asm.feed(d))
                LOG.info("connected; polling every %ss", args.interval)

                while client.is_connected:
                    status = {}
                    basic = await asm.request(client, REQ_BASIC)
                    if valid_frame(basic) and basic[1] == 0x03:
                        parse_basic(basic, status)

                    cells = await asm.request(client, REQ_CELLS)
                    if valid_frame(cells) and cells[1] == 0x04:
                        parse_cells(cells, status)

                    if "voltage" in status:
                        mq.publish(args.topic, json.dumps(status), qos=0)
                        LOG.debug("published %s", status)
                    await asyncio.sleep(args.interval)

        except Exception as e:
            LOG.warning("BLE session ended (%s); retrying in 10s", e)
            await asyncio.sleep(10)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mac", required=True, help="BMS BLE MAC address")
    ap.add_argument("--broker", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--topic", default="camper/battery/houseBattery")
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("-v", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.v else logging.INFO)
    asyncio.run(run(args))
