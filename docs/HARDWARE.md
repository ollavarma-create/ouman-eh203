# Hardware and connection notes

Tested with an EH-203 bench unit, native RS-232 connector and a PL2303 USB–RS232 adapter (`067b:2303`) on Fedora, typically `/dev/ttyUSB0`. Port: **4800 8N1**, flow control disabled. An adapter-local loopback returned 256/256 test bytes correctly. Controller output was measured around **−9 V**; PC adapter exhibited true RS-232 levels.

**Do not connect ESP32 GPIO or TTL UART directly** to the controller's RS-232 signals. An ESP32 interface will require a MAX3232-class level transceiver and a common signal ground. Validate the actual controller terminal wiring on the bench before connection; earlier experiments required swapping the assumed RX/TX direction. This document deliberately does **not** provide an unverified Ouman terminal pinout.

Sensor fault probing: disconnecting a sensor produced LCD `Err`, an audible alarm and response raw `86 5A` on an affected measurement. No short-circuit fault tests were performed.

The native serial interface differs from an optional Modbus configuration/interface. Do not assume Modbus RTU addressing or register maps.

References (manufacturer documents):
- https://ouman.fi/documentbank/EH-203__manual__fi.pdf
- https://ouman.fi/documentbank/MODBUS-200__manual__en.pdf
