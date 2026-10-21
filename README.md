# LAN Audio (Ubuntu -> Android browser)

A minimal local-network prototype that captures a PulseAudio-compatible **output monitor**
and streams it to up to three Android browser clients using WebRTC.

## 1. Install system dependencies

On Ubuntu:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip ffmpeg pulseaudio-utils
```

PipeWire users normally have a PulseAudio-compatible server. Check:

```bash
pactl info
pactl list short sources
```

Find the source corresponding to the laptop's output device. It usually ends in
`.monitor`, for example `alsa_output.pci-0000_00_1f.3.analog-stereo.monitor`.
**Do not choose a source named `alsa_input...` or one corresponding to a microphone.**

If the source list has no monitor source, first check that the output device is playing audio
and that PipeWire/PulseAudio is running.

## 2. Create the Python environment

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Set the output monitor and run

Copy the exact monitor source name from `pactl list short sources`:

```bash
export AUDIO_SOURCE='PASTE_YOUR_OUTPUT_MONITOR_SOURCE_HERE'
export MAX_CLIENTS=3
python app.py
```

The audio capture runs as the logged-in desktop user, so run this from the same Ubuntu user
session that owns the audio server; avoid `sudo`.

## 4. Connect Android phones

1. Put the host and phones on the same Wi-Fi network. Guest Wi-Fi or AP/client isolation must
   be disabled.
2. Find the laptop's LAN IPv4 address, for example with `hostname -I`.
3. On each phone, open `http://LAPTOP_IP:8000`.
4. Pair each phone with its Bluetooth earbuds.
5. Tap **Start listening** and press Play if the browser requires it.

For example, if the host IP is `192.168.1.20`, open `http://192.168.1.20:8000`.

## Troubleshooting

- **No audio:** verify the chosen source is the output `.monitor`, and play sound on the laptop.
- **Server errors at startup:** verify `AUDIO_SOURCE` is set and `pactl info` works as the same user.
- **Phone cannot connect:** verify both devices are on the same Wi-Fi, disable client isolation, and
  allow TCP port 8000 in the host firewall if enabled.
- **Connection connects but audio does not play:** tap Play on the page's audio control and check
  Android media volume / Bluetooth output.
- **Audio cuts out or latency is too high:** test with one phone first, keep the Wi-Fi signal strong,
  and close other heavy network/audio workloads.

## Notes / limitations

- This prototype uses a separate WebRTC peer connection for each listener and no external STUN/TURN
  servers. It is intended for clients on the same LAN.
- The web page never calls `getUserMedia`, so it does not request microphone access.
- A monitor source captures the system output sent to that audio sink. If the laptop switches
  output devices, select the corresponding monitor source and restart the server.
- Browser, operating-system and Bluetooth buffering vary, so exact synchronization across phones
  is not guaranteed. Bluetooth itself adds latency.
- This starter is not hardened for untrusted networks. Anyone able to reach the host and its port
  can try to listen; use only a trusted network until room authentication is added.
