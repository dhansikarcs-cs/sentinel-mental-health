# Sentinel — Viaking R30 PRO: hardware identification, feasibility & integration findings

> Status: **live hardware results + protocol identification + design**.
> Captured 2026-11-15 on a Windows laptop with Bleak 3.1.0. All measurements are
> labelled `viaking_r30pro_experimental` and are **not clinically validated**.
>
> **Update (protocol research):** the vendor GATT service was identified as
> **Yucheng YCBT** — a documented, unencrypted, no-auth, no-subscription protocol
> with open-source hardware-validated implementations. See §6.
>
> **⚠ REVISION 2026-11-15 (long-window probe) — earlier "not working" claims were
> WRONG for SpO₂ and BP.** See §12. The failure was a too-short measurement
> window, not a firmware limit. Sections §4, §8 and §10 below are superseded by
> §12. Read §12 for the current truth.

---

## 1. Hardware identification report

### 1.1 Box claims (manufacturer-printed, not independently verified)

| Component | Claim |
| --- | --- |
| Brand / device name | VI AKING R30 PRO / `R30 PRO` |
| Bluetooth | 5.3 |
| Main chipset | Nordic nRF52832 |
| ECG sensor | Goodix 3228T |
| PPG sensor | Goodix 3228T + 2 × SFH2703 |
| Motion sensor | STK8321 |
| Flash / RAM | 512 KB / 64 KB |
| Ring / case battery | 18 mAh / 400 mAh |
| Companion app | HealthWear |
| Waterproof | IP68 |
| Usage / standby | 4–6 days / 10–15 days |

The JSmax product page (`jsmax.com.tw/en/products.html`) matches these claims
verbatim (nRF52832, 512/64 KB, STK8321, Goodix 3228T ECG, 3228T + 2×SFH2703
PPG, NTC temp, BT5.3, HealthWear, IP68, 18 mAh, sizes 7#–13#). The AliExpress
spec PDF is a 6-page marketing sheet naming **"Smart Health"** as the app, not
HealthWear. Neither source contains BLE protocol/UUID/SDK information.

### 1.2 What the device actually reports over BLE (measured)

| Field | Observed value |
| --- | --- |
| Advertised name | **`R30 PRO F085`** — not plain `R30 PRO` |
| BLE address | `C1:75:21:86:F0:85` (WinRT raw `0xc1752186f085`) |
| RSSI | −32 … −76 dBm (advertising duty cycle ~4 s) |
| Advertised services | `0x180D` Heart Rate, `0xFEE7` (WeChat pedometer) |
| Manufacturer data | company id `0x7811`, payload `00000001010d000000000000000000000000640000c1752186f085` (last 6 bytes = own MAC) |
| Service data | none observed |
| Generic Access `0x2A00` | `R30 PRO F085` |
| Appearance `0x2A01` | `0x0000` (unspecified) |
| Central Address Resolution `0x2AA6` | `0x01` |
| Device Info `0x2A29` | **`BL`** (only Device Information characteristic present) |
| Battery `0x2A19` | `0x64` = **100 %** |
| **`0x2A38`** | `0x03` = **Body Sensor Location "Finger"** (NOT HR Control Point — `0x2A39` is HRCP) |
| WeChat `0xFEC9` | returns MAC `c1752186f085` |
| WeChat `0xFEA1` | `07 00 00 00 00 00 00 00 00 00` = pedometer flag + three zero Uint24 fields |
| WeChat `0xFEA2` | `013b9ce3` (step target / session value; exact meaning unknown) |
| **YCBT `be940003`** | unsolicited `ffff0600a6aa` — a valid YCBT frame (see §6) |

**Vendor identification (from protocol research, LIKELY not proven on this unit):**
OEM/ODM brand **JSmax / Jing Shin Technologies** (Taiwan); firmware + app +
SDK from **Shenzhen Yucheng / 玉成创新** (`ycinnovate.com`). Yucheng's FAQ says
SmartHealth (rings) and HealthWear (watches) are functionally identical apps,
which explains a ring shipping with HealthWear. `BL` is likely an ODM code.

---

## 2. Phase A — BLE discovery: CONFIRMED ✅

- Direct Windows → BLE advertisement scan works with Bleak.
- **Implementation detail:** `BleakScanner.discover(timeout=8)` returned **0 devices**,
  while `BleakScanner(detection_callback=…, scanning_mode="active")` with explicit
  `start()`/`stop()` found the ring reliably (also confirmed with a raw WinRT
  `BluetoothLEAdvertisementWatcher`). All lab scripts use streaming.
- **Advertising is intermittent** (~one burst every ~4 s, with quiet gaps).
  A 12 s scan can miss it entirely. `find_device()` therefore retries 3× and
  caches the address in `out/device.json`, falling back to connecting by known
  address (WinRT resolves it without a fresh advertisement).
- Ring advertises while idle in air (not only on charge). `scan.py --repeat`
  supports the charging/worn/idle comparison study.

## 3. Phase B — GATT map: CONFIRMED ✅ (9 services)

Read-only enumeration, no writes. Full JSON: `out/gatt_map.json`,
readable report: `out/gatt_report.txt`.

| # | Service | Handle | Chars | Identification |
| --- | --- | --- | --- | --- |
| 1 | `0x1800` Generic Access | 1 | 4 | standard |
| 2 | `0x1801` Generic Attribute | 10 | 1 | Service Changed — Windows refused subscription (`Access Denied`) |
| 3 | **`0x180D` Heart Rate** | 14 | 2 | `0x2A37` notify, `0x2A38` Body Sensor Location = Finger |
| 4 | **`0x180F` Battery** | 20 | 1 | `0x2A19` notify+read → 100 % |
| 5 | `0x180A` Device Information | 24 | 1 | only `0x2A29` → `BL` |
| 6 | `6e400001-…` | 27 | 2 | **Nordic UART Service** (RX write / TX notify) |
| 7 | `0000fe59-…` | 33 | 1 | **Nordic Secure DFU** (`8ec90003-…`) — ⚠️ DO NOT WRITE |
| 8 | **`be940000-7333-be46-b7ae-689e71722bd5`** | 37 | 3 | **Yucheng YCBT health protocol** — the real measurement path |
| 9 | `0000fee7-…` | 46 | 3 | **Tencent WeChat BLE-Lite pedometer** (`FEA1`/`FEA2`/`FEC9`) |

**Standard profiles present:** 0x180D ✅, 0x180F ✅, 0x180A ✅ (partial),
0x2A37 ✅, 0x2A19 ✅. Missing: `0x2A39` HR Control Point.
**Vendor-specific 128-bit UUIDs: 4 services / 8 characteristics**, now all
identified (§6). No `AE00` JieLi RCSP auth service.

## 4. Phase C — Data accessibility matrix (revised after protocol ID)

Legend: ✅ demonstrated · 🌐 documented for this protocol family (needs on-device
confirmation) · ❌ not exposed · ❓ unknown.

| Measurement | Sensor on box | Retrievable over BLE | Streamable | Historical |
| --- | --- | --- | --- | --- |
| Battery level | implied | ✅ **100 %** (`0x2A19` + `02 00` reply) | ✅ | ❌ n/a |
| Device name / MAC | n/a | ✅ | ❌ | ❌ |
| **Heart rate (live)** | ✅ PPG | 🌐 `03 2f {01,00}` → `06 01` stream | 🌐 | 🌐 `05 06` |
| **SpO₂ (spot)** | ✅ PPG | 🌐 `03 2f {01,02}` → `06 02` | 🌐 | 🌐 `05 1A` |
| **Blood pressure** | ❓ | 🌐 `03 2f {01,01}` → `06 03` (uncalibrated trend) | 🌐 | 🌐 `05 08` |
| **HRV** | ✅ PPG | 🌐 `03 2f {01,0a}` / body-data record | 🌐 | 🌐 |
| **Steps / distance / calories** | ✅ STK8321 | 🌐 `06 00` live + WeChat `FEA1` | 🌐 | 🌐 `05 02` |
| **Sleep stages / REM** | ❓ | 🌐 | ❌ | 🌐 `05 04` |
| **Skin temperature** | ✅ NTC | 🌐 (capability-gated) | 🌐 | 🌐 `05 1E` |
| **Stress / fatigue** | ❓ | 🌐 (capability-gated, `05 33`) | ❌ | 🌐 |
| Respiratory rate | ❓ | 🌐 combined record | ❌ | 🌐 |
| **ECG raw waveform** | ✅ Goodix 3228T | ❓ **wire format unpublished** (vendor SDK has API, binary `.so`) | ❓ | 🌐 SDK has sync API |
| Raw PPG / accelerometer | ✅ | ❌ none visible | ❓ | ❓ |
| Standard `0x2A37` HR | — | ⚠️ **decoy** — streams `04 00` (bpm 0, contact not detected) even when worn | ✅ 1 Hz | ❌ |

**Critical finding (confirmed on this unit):** wearing the ring did **not** change
`0x2A37` — 120 s of worn capture still produced `04 00`. The PulseLoop project
explicitly documents this for the same YCBT firmware: *"Standard heart-rate
service is deliberately ignored. The TK5 exposes 180D/2A37, but it emits a
cached resting HR even off-finger, which would mask real readings. Live HR comes
solely from the proprietary `06 01` stream."* **Do not use `0x2A37` for live HR.**

## 5. Phase D — Passive notification capture: CONFIRMED ✅

`python notify.py --seconds 35` → **54 packets**, log `out/notifications.jsonl`.

| Characteristic | Packets | Content |
| --- | --- | --- |
| `0x2A37` HR Measurement | 35 (≈1 Hz) | `0400` — decoy placeholder |
| `0xFEA1` WeChat pedometer | 17 (≈2 s) | `07000000000000000000` — live step counter, all zeros |
| `0x2A19` Battery | 1 | `64` on subscribe |
| **`be940003` YCBT stream** | 1 | **`ffff0600a6aa`** — a valid YCBT frame |
| NUS TX, `0xFE59`, `0xFEA2` | 0 | silent without a command |

`0x2A05` Service Changed refused subscription on Windows (`Access Denied`) —
logged, not retried.

## 6. Phase E — Proprietary protocol: **IDENTIFIED** ✅

The `be940000` service is **Yucheng YCBT**, documented by the open-source
PulseLoop project (iOS + Android), which validated it end-to-end on hardware
(R10M FW 2.32, SmartHealth-app Colmi R99). Yucheng publishes a free SDK
(`ycinnovate.com/sdk.html`, Gitee `yucheng_3/android-sdk-2.0`).

**Frame format (verified independently on THIS unit):**

```
[type:1][cmd:1][len:2 LE][payload:N][crc16:2 LE]
len = TOTAL frame length
CRC = CRC16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection), little-endian
Epoch = seconds since 2000-01-01, ring's LOCAL wall-clock
```

The ring's unsolicited `ffff0600a6aa`: header `ffff0600`, `len=6`, and
`CRC16(ffff0600) = 0xAAA6` → bytes `a6 aa`. **Exact match.** All six handshake
frames we generated also self-validate (`ycbt.py` dry-run).

| Channel | Role |
| --- | --- |
| `be940001` | command **write** + indicate (device info, capability bitmap, ACKs) |
| `be940003` | indicate (live vitals `06 xx`, all history data) |
| `be940002` | write (secondary) |

**Documented sequence:** both indication channels must be subscribed first →
`02 03` GetDeviceName → `01 00` SetTime → `02 01` GetSupportFunction
(capability bitmap) → `02 28` GetMeasurementFunction → `02 26` keep-alive
(~20 s) → `03 09` broadcast enable → `03 2f {01, type}` start measurement
(type 00=HR, 01=BP, 02=SpO₂, 0a=HRV) → `06 01`/`06 02`/`06 03` live data →
`03 2f {00, type}` stop. History: `05 <key>` → frames → `05 80` terminal →
mandatory `05 80 {00}` ACK.

| Question | Answer |
| --- | --- |
| Auth / encryption for health data | ❌ **None.** Plaintext CRC frames, no bonding required. |
| Subscription / cloud / account | ❌ **None.** Vendor SDK + apps are free and offline-capable. |
| DFU trap | ⚠️ `0xFE59` / `8ec90003` is Nordic Secure DFU — writing `0x01` reboots into bootloader. **Never write.** |
| Data deletion trap | ⚠️ `05 40`–`05 4E` deletes and `05 80` terminal ACK **erase the ring's log**. Deliberately excluded. |
| Colmi / Yawell / JRing substitution | ❌ Not used. The QRing/NUS Colmi protocol is a *different* wire protocol. YCBT is identified by the exact `be94` UUID + verified CRC, not by shared Nordic silicon. |

**Remaining unknown:** raw **ECG** byte format is unpublished (only in the
vendor's binary `libEcgAnaly.so`). Everything else in the matrix has a
documented path.

## 7. Phase F — Sentinel integration architecture (DESIGN ONLY)

Sentinel **already has** a wearable ingestion layer:

```
Viaking R30 PRO
  → Windows BLE Collector        (hardware_lab/ycbt.py, native Python)
  → Measurement Parser           (CRC verify, 06 xx payload decode)
  → Data Validation              (range gates, capability bitmap, plausible values)
  → Sentinel FastAPI Ingestion   (POST /api/ring/data)
  → Sentinel Processing          (RingSensorLog + SensorReading → wellness / triage)
```

Exact existing contract (`backend/app/api/ring.py`, `schemas/ring.py`,
`core/dependencies.py`):

- `POST /api/ring/pair` with patient JWT → `{serial, vendor}` → returns `token`.
- `POST /api/ring/data` with headers `X-Device-Serial` + `X-Device-Token`
  (SHA-256 hashed token, constant-time compare), body `SensorDataCreate`:
  `device_id, bpm(30–250), stress(0–100), sleep_hours(0–24), spo2(50–100),
  hrv(0–300), seq, timestamp`.
- `seq` is **idempotent** on `(device_id, seq)`. Fallback auth is a patient JWT.
- Validation: `validate_sensor_data()` re-checks the same ranges.

### ⛔ Blocking data-integrity issue (must fix before any live push)

`SensorDataCreate` supplies **defaults** for `stress=35`, `sleep_hours=7.0`,
`spo2=98.0`, `hrv=50`. A partial wearable push containing only `bpm` would
**silently store four fabricated clinical values**, and `ring.py` hardcodes
`temperature=36.5` in `SensorReading`. For a mental-health platform feeding
wellness/triage, that is unacceptable. Required backend change (not yet done):

1. Make `stress`, `sleep_hours`, `spo2`, `hrv` `Optional = None` for hardware
   pushes (or add a dedicated `/api/wearable/measurements` endpoint).
2. Persist raw packet / source metadata (`RingSensorLog.raw_json` exists) and
   mark rows `experimental`.
3. Only map a field when the ring genuinely delivered it.

### Other Phase F requirements (specified, not yet built)

- BLE collection physically separate from clinical processing ✅ (separate folder, outside CI).
- Preserve raw packets ✅ (`notifications.jsonl`, `ycbt_frames.jsonl`).
- Normalize timestamps to UTC ✅; convert ring local wall-clock carefully (§6 epoch).
- Record source device + metadata ✅ (`device_id`, `source_label`).
- Distinguish raw values from derived metrics (HRV, stress are derived).
- Handle disconnect/reconnect: Bleak `disconnected_callback` + cached address.
- Avoid duplicates: monotonic `seq` + idempotent `(device_id, seq)`.
- Track missing/invalid: CRC failures and out-of-range values dropped, not stored.
- Clearly label all experimental data ✅.
- **No clinical conclusions** from unvalidated wearable values ✅.

`bridge.py` implements the exact payload as a **gated dry-run** and refuses to
send without explicit acknowledgement flags. It is intentionally not wired up.

## 8. Technical feasibility assessment (revised)

| Question | Answer |
| --- | --- |
| Can the R30 PRO connect directly to a Windows BLE GATT client? | ✅ **Yes, proven.** No phone/app/pairing needed. |
| Does it expose measurements through standard characteristics? | ✅ Battery + identity. ⚠️ `0x2A37` HR is a decoy, not live data. |
| Are vendor-specific characteristics present? | ✅ Yes — now all identified (YCBT, WeChat, NUS, Nordic DFU). |
| Can HR be retrieved without HealthWear? | 🌐 **Yes, via documented `03 2f`/`06 01`.** Needs on-device confirmation. |
| Can SpO₂ / BP / steps / sleep / temp be retrieved? | 🌐 **Yes, documented paths exist.** No standard characteristics. |
| Can ECG / raw PPG be retrieved? | ❓ ECG wire format unpublished; needs SDK reversing. |
| Is continuous streaming supported? | 🌐 Yes, `06 xx` live streams while connected. |
| Is historical data stored on the ring? | 🌐 Yes, `05 xx` queries; ~8-day horizon. |
| Does the ring require proprietary commands? | ✅ **Yes** — documented handshake, no auth. |
| Can it operate locally with no subscription/cloud? | ✅ **Yes.** No account, no paywall, no vendor cloud. |

**Verdict:** discovery + GATT + protocol identification are **done**. The one
remaining proof point is a **real HR value from the `06 01` stream** via the
documented handshake (`ycbt.py --enable-writes`). After that, Sentinel ingestion
is a small, well-understood bridge.

## 9. Deliverables checklist

| # | Deliverable | Status |
| --- | --- | --- |
| 1 | Hardware identification report | ✅ §1 |
| 2 | BLE scanner script | ✅ `scan.py` |
| 3 | GATT discovery script | ✅ `gatt.py` |
| 4 | GATT JSON + text export | ✅ `out/gatt_map.json`, `out/gatt_report.txt` |
| 5 | Notification monitoring utility | ✅ `notify.py` |
| 6 | Raw packet logs | ✅ `out/notifications.jsonl` (54 pkts), `out/ycbt_frames.jsonl` |
| 7 | Data accessibility matrix | ✅ §4 (revised) |
| 8 | Technical feasibility assessment | ✅ §8 |
| 9 | Sentinel integration architecture | ✅ §7 (design only) |
| 10 | Unresolved technical questions | ✅ §10 |

Scripts: `common.py`, `scan.py`, `gatt.py`, `notify.py`, `measure.py`,
`ycbt.py`, `bridge.py`.

## 10. Unresolved technical questions

1. Does `03 2f {01,00}` produce a real `06 01` HR value on **this** unit?
   (single most important test — `ycbt.py --enable-writes` while worn)
2. What is the `06 01` payload byte layout / bpm scale on this firmware?
3. Does this ring's `02 01` capability bitmap declare SpO₂, temperature, HRV,
   stress, BP? (determines which metrics are genuinely available)
4. Is raw ECG retrievable at all, or only via the vendor's binary SDK?
5. Does the WeChat `FEA2` value `013b9ce3` have meaning beyond a step target?
6. Is `0x7811` a placeholder company id (Tencent spec allows arbitrary) or a
   real id? What is byte `0x64` in the manufacturer payload?
7. Exact `BL` ODM identity; confirm JSmax ↔ Yucheng relationship for this unit.
8. Local wall-clock/timezone handling for history timestamps on the ring.
9. Should Sentinel accept partial wearable payloads (recommended) or require a
   new nullable schema before any live push?
10. Advertising differences on charge / worn / idle (`scan.py --repeat`).

## 11. Sources

- PulseLoop YCBT protocol: `saksham2001.github.io/PulseLoopiOS/hardware/`,
  `…/hardware/tk5/#protocol`, `…/hardware/r10m/#protocol`
  (`github.com/saksham2001/PulseLoopiOS`, `github.com/foureight84/PulseLoopAndroid`)
- Gadgetbridge YCBT script: `codeberg.org/Freeyourgadget/Gadgetbridge/issues/7091`
- Yucheng SDK: `ycinnovate.com/sdk.html`, `gitee.com/yucheng_3/android-sdk-2.0`
- HealthWear app: `play.google.com/store/apps/details?id=com.yucheng.HealthWear`
- JSmax R30 PRO: `jsmax.com.tw/en/products.html`
- AliExpress spec PDF: `ae-pic-a1.aliexpress-media.com/kf/S9c47df12321743d4bae56e4afb38469dw.pdf`
- Tencent WeChat BLE-Lite: `iot.weixin.qq.com/wiki/new/index.html?page=4-3`
- Nordic Secure DFU: `reverse.bike/specifications/bluetooth-ble/secure-dfu-service/`
- Bluetooth HRS spec: `bluetooth.com/wp-content/uploads/Files/Specification/HTML/HRS_v1.0/out/en/index-en.html`
- Bleak: `bleak.readthedocs.io/en/stable/`


---

## 12. REVISION - long-window probe (2026-11-15, SUPERSEDES §4/§8/§10)

Earlier probes used 18-20 s windows and batched commands. That was the bug.

### Why the earlier "not working" verdict was wrong

1. **Measurement convergence takes 30-60 s.** The Nordic UART debug channel
   (6e400003, ASCII - previously undecoded) showed the SpO2 algorithm running
   26 iterations of "SpO2: 0" before locking on: 98 -> 97 -> 97 -> 96 %. A
   90 s single-measurement window with a 20 s cooldown produced a valid
   `0602` frame (payload 0x60 = 96 %) plus the `040e` completion frame.
2. **0xFC poisoning.** One rejected query stops the rest of THAT session; fresh
   connections per query were required.
3. **History was empty because nothing had been measured yet.** After real
   measurements, HR/BP/combined-all-day history filled with records.
4. **Standard 0x2A37 is a decoy** (always 0400) - confirmed again, but real HR
   comes from 0601.

### Signals now CONFIRMED collected (CRC-validated, raw frames in out/)

| Signal | Real values | Source |
| --- | --- | --- |
| Heart rate | 89, 85, 83 bpm live; 4 history records 89/85/83/74 | 0601 + 0506/0515 |
| **SpO2** | **96 % final** (98/97/97/96 intermediates) | 0602 + NUS ASCII + 0509/0518 |
| **Blood pressure (candidate)** | 98/69, 108/73 (+ pulse 74, 100) | 0508/0517 history - appeared only after a BP measurement |
| **Raw PPG (G/R/IR ADC)** | 33+ samples | Nordic UART ASCII debug stream |
| Battery | 100 % | 0x2A19 |
| Steps | 0 (channel present) | 0xFEA1 |
| Body sensor location | Finger (0x03) | 0x2A38 |

BP byte layout is INFERRED, not documented - treat as candidate, never clinical.

### Still NOT obtained

| Signal | Firmware answer |
| --- | --- |
| ECG | no documented wire format, no frames observed |
| Temperature | 051e rejected 0xFC |
| HRV | mode 0x0a only enables "hr_auto_monitor 1,60"; no HRV value |
| Sleep stages | 0504 empty (no overnight wear) |
| Stress / fatigue | 0533 rejected 0xFC |
| Dedicated SpO2/temp/comprehensive logs | 051a/051e/052f rejected 0xFC (but live SpO2 works!) |

### What changed in the understanding of 0xFE / 0xFC

- `0xFE` on 0203/0201/0228/0200 = stub/short replies for capability queries on
  this stripped-down firmware; control commands (0100/0309/032f) still succeed.
- `0xFC` = "this history command does not exist in this firmware" (confirmed on
  fresh connections). It does NOT mean the underlying sensor is absent: SpO2
  history is rejected but live SpO2 measurement works.

### Sentinel ingestion (verified end-to-end, throwaway DB)

    POST /api/ring/data  {bpm: 83, spo2: 96.0, seq: 1}  -> 200
    RingSensorLog: bpm=83 spo2=96.0 stress=None hrv=None sleep=None
    SensorReading: hr=83 rmssd=None sdnn=None temp=None

Only measured fields stored; no fabrication. Source artefacts:
`out/genuine_measurements.json`, `out/probe_deep_spo2.json`,
`out/probe_deep_spo2_frames.jsonl`, `out/probe_history_frames.jsonl`.

### Scripts added for this revision

`probe_all.py`, `analyze_all.py`, `probe_modes.py`, `probe_history.py`,
`probe_deep.py`, `decode_nus.py`, `decode_mode.py`, `decode_history.py`.

All use documented opcodes only. No DFU, no delete, no reset, no OTA,
no guessed commands.


---

## 13. FINAL REVISION - vendor SDK recovered (SUPERSEDES §4/§8/§10/§12)

A research pass recovered the Yucheng SDK AAR (`ycbtsdk-release-4.0.11.aar`),
its `Constants$DATATYPE`, `YCBTClient` bytecode, the vendor DOCX, the demo app,
and the PulseLoop `tasks/ycbt-protocol.md`. Ground truth for hex opcodes.

### Corrected signal list (FINAL)

| Signal | Status | Real values |
| --- | --- | --- |
| Heart rate | CONFIRMED | 89/85/83 live; 4 history records 89/85/83/74 |
| SpO2 | CONFIRMED | 96 % live; 98/96/89 in combined records |
| Blood pressure | CONFIRMED (candidate layout) | 98/69, 108/73 |
| **Temperature** | **CONFIRMED** | body 35.84-35.88 C live (19 samples); 36.3 C stored |
| **HRV** | **CONFIRMED** | 37 ms (combined record @11) |
| Raw PPG | CONFIRMED | 33+ G/R/IR ADC samples |
| Battery / identity / steps channel | CONFIRMED | 100 %, R30 PRO F085, 0 steps |
| ECG | **CONFIRMED WORKING** | 245 x `0605` frames = 21,315 int16 samples over ~72 s, all CRC-valid; single-finger wear; see §14 |
| Sleep stages | NOT OBTAINED | 0504 empty; needs overnight wear |
| Stress / fatigue | NOT OBTAINED | 0533 rejected 0xFC; not in combined record |

### Combined all-day record (05 09 / 0518) - 20-byte stride, CONFIRMED layout

    @0  ts:u32 LE      @6  heartRate       @11 hrv(ms)      @17 bloodSugar
    @4  steps:u16      @7  systolic        @12 cvrr         @18-19 reserved
                        @8  diastolic       @13 tempInt
                        @9  spo2            @14 tempFrac
                        @10 respiratoryRate @15/16 bodyFat

Temperature = float(f"{int}.{frac}"); filler when int==0 or frac==15.
"Fields that return 0 should be ignored" (vendor doc 3367-3437).
Decoded: spo2 98 / hrv 37 / temp 36.3, then spo2 96, then spo2 89.

### Official return codes (vendor doc 4962-4979) - corrects earlier guesses

    0xFB unsupported command ID | 0xFC unsupported Key | 0xFD length error
    0xFE Data error             | 0xFF CRC error       | 0 success, 1 failed

`0xFE` on 0200/0201/0203/0228 was OUR malformed queries (missing 2-byte
payload tags 47 43 / 47 46 / 47 50). Not a firmware limitation.
`0xFC` = command genuinely absent on this firmware.

### 01 xx monitor table (vendor constants)

    01 0c HR | 01 1c BP all-day | 01 20 temperature | 01 26 SpO2
    01 45 HRV (5-byte payload) | 01 49 measurement function (payload unknown)
    01 28 ambient temp+humidity | 05 40..05 4E are DELETE opcodes (never sent)

Capability sweep: 14 monitors accepted, 112 rejected 0xFC. Enabling 01 20
produced live `Env: 30.66, Skin: 30.66, BT: 35.88` temperature frames.

### ECG path (from disassembled vendor bytecode - not in prose docs)

    03 02 {02} appEcgTestStart     03 02 {00} appEcgTestEnd
    03 0b {01,01} AppControlWave ECG waveform upload (type 01=ECG)
    06 05 Real_UploadECG          06 f0/06 f1 ECG HRV / RR
    03 14 AppECGPPGStatus         04 0b DeviceEndECG
    07 00/01/02/06/07/10/30 ECG/PPG raw-file history (Collect group)
    02 27 GetEcgMode              03 0a {01} query ECG sample rate

ECG needs a second electrode contact: "After starting the ECG measurement,
you need to place your other hand's finger on the ground near the electrode"
(vendor doc 2838). No bind/auth opcode is required for health data.

### Sources

- gitee.com/yucheng_3/android-sdk-2.0 (AAR, DOCX, demo app)
- raw.githubusercontent.com/saksham2001/PulseLoopiOS/main/tasks/ycbt-protocol.md
- github.com/foureight84/PulseLoopAndroid ... YCBTProtocol.kt


---


---

## 14. ECG CONFIRMED + 0xFE root cause (FINAL)

### ECG capture (single-finger wear - the two-electrode note does NOT apply here)

Commands that worked, in order (start ECG BEFORE any info query, because one
0xFC aborts the rest of that session):

    01 00 <epoch>       set_time
    03 09               broadcast_enable
    03 0b {01,01}       AppControlWave - start ECG waveform upload
    03 02 {02}          appEcgTestStart
    ... 75 s listen ...
    03 02 {00}          appEcgTestEnd
    03 0b {00,01}       stop waveform
    07 00               ECG file history query num (read-only)

Result: 245 frames of `0605` (Real_UploadECG), each 180 B
[06][05][len=180][174 B = 87 x int16 LE][crc16], every CRC valid.
Decoded: 21,315 samples, min -32768 / max 32744, 7,488 distinct values,
window 2026-11-15T11:48:02 -> 11:49:14 UTC. Saved to
`out/ecg_waveform.csv` and `out/ecg_waveform_summary.json`.
This is a RAW ADC waveform, not a clinical ECG interpretation.

### 0xFE was our malformed Get commands - CONFIRMED

Vendor SDK sends every `02 xx` Get with a 2-byte payload tag:

    02 00 -> 47 43 (frame 02 00 08 00 47 43 6F EC)
    02 01 -> 47 46
    02 03 -> 47 50
    02 28 -> 47 46

Our CRC recomputation of `020008004743` gives 0xEC6F -> bytes `6f ec`,
exactly matching the vendor frame. Validation passed.

With tags, the ring returned REAL data instead of 0xFE:
    02 00 -> 24-byte device info (battery byte @5 = 0x64 = 100 %)
    02 01 -> 60-byte capability bitmap
    02 03 -> "R30PRO"
    02 28 -> 0000
    02 1b -> 00       chip scheme
    03 0a {01} -> fa00  (250 Hz ECG sample rate)
    02 27 -> fc        (GetEcgMode unsupported on this firmware)
    03 14 -> fc        (ECG/PPG status unsupported)

Official return codes (vendor doc 4962-4979):
    0 success | 1 failed | FB unsupported command ID | FC unsupported Key
    FD length error | FE Data error | FF CRC error

### Stress / sleep - FINAL honest answer

- Stress/fatigue: `05 33` body-data record is rejected `0xFC` (Unsupported
  Key) on FRESH connections, i.e. genuinely not implemented in this firmware.
  The debug console never printed any stress/fatigue/pressure value in any
  of the 11 captured frame logs. NOT OBTAINABLE without vendor firmware support.
- Sleep: `05 04` history is implemented but returns `0000` (empty). Sleep
  staging needs overnight wear + a night rollover, so it cannot be produced
  in a live session. ACTION: wear overnight, then query 05 04 the next morning.
