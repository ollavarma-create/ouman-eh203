# Raw experiment capture inventory

Each `ouman_*.json` file contains one read-only parameter sweep with entries keyed by queried ID, including `tx`, `rx`, `valid`, `rejected`, `payload` (which includes echoed `00 ID`), and `response_ms`. All files were uploaded into the research chat; this document records their names and experimental meaning. **Raw captures have not yet been committed here**; upload the immutable originals separately.

## Baselines, fault exploration and broad sweep
- `ouman_normal.json`: normal baseline.
- `ouman_fault.json`: outdoor sensor open/fault state.
- `ouman_l1_open.json`: L1 supply sensor open.
- `ouman_l1_ack.json`: L1 supply fault acknowledged.
- `ouman_l1_restored.json`: L1 supply connected again.
- `ouman_scan_64_127.json`: read sweep IDs 64–127.

## L1 and general controller settings
- `ouman_l1_min16.json`: L1 supply minimum 15→16.
- `ouman_l1_max51.json`: L1 supply maximum 50→51.
- `ouman_l1_night3.json`: night reduction 0→3.
- `ouman_l1_shift_minus2.json`: L1 parallel shift 0→−2.
- `ouman_l1_autumn3.json`: autumn drying 2→3.
- `ouman_l1_valveclose20.json`: Vent.keskisulk 19→20.
- `ouman_l1_outdoor_delay3.json`: outdoor-temperature delay 2→3 hours.
- `ouman_l1_trend5.json`: L1 trend sampling 1→5 seconds; change not found in scanned ID range.
- `ouman_l1_p150.json`: L1 P 140→150.
- `ouman_l1_i60.json`: L1 I 50→60 s.
- `ouman_l1_d15.json`: L1 D 0.0→1.5 s.
- `ouman_l1_motor160.json`: L1 actuator travel 150→160 s.
- `ouman_l2_p160.json`: L2 P 140→160.
- `ouman_l1_alarm26.json`: L1 deviation alarm 25→26.
- `ouman_l2_alarm26.json`: L2 deviation alarm 25→26.
- `ouman_alarmdelay61.json`: deviation alarm delay **60→70 minutes**, despite filename suffix `61`.
- `ouman_return_max71.json`: return maximum 70→71 °C.
- `ouman_return_min0_6.json`: return min at 0°C, 5→6.
- `ouman_return_min20_16.json`: return min at −20°C, 15→16.
- `ouman_l1_supply_min0_11.json`: L1 supply min at 0°C, 10→11.
- `ouman_l1_supply_min20_31.json`: L1 supply min at −20°C, 30→31.

## DHW (LV)
- `ouman_lv_setpoint59.json`: DHW setpoint 58.0→59.0.
- `ouman_lv_fastdrive65.json`: DHW fast drive 60→65%.
- `ouman_lv_feedforward150.json`: DHW feedforward 140→150°C.
- `ouman_lv_p80.json`: DHW P 70→80.
- `ouman_lv_i20.json`: DHW I 18→20s.
- `ouman_lv_d15.json`: DHW D 0→1.5s.
- `ouman_lv_alarm26.json`: DHW deviation alarm 25→26.
- `ouman_lv_alarmdelay610.json`: DHW alarm delay 600→610s.

Other source reference files: `EH-203.xml` and `EH-203.dev` describe **Modbus** capabilities, not the native serial byte map. Observe Ouman's copyright/license before redistributing vendor content.

## L2 supply limits
- `ouman_l2_supply_min0_11.json`: 10→11°C at 0°C outdoor.
- `ouman_l2_supply_min20_31.json`: 30→31°C at -20°C outdoor.

- `ouman_l2_min16.json`: ordinary L2 supply minimum 15→16°C.
- `ouman_l2_max71.json`: ordinary L2 supply maximum 70→71°C; latest capture.
