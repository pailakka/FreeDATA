import datetime
import json
import os
import queue
import subprocess
import sys
import threading
import time
import webbrowser

import serial.tools.list_ports

import audio

DO_EXIT = False
VERBOSE = False

MISSING_NEEDLES = {}

def device_input(devices, q, header, default):
    print(header)
    for d in devices:
        print(f'{d["id"]}: {d["name"]}')
    input_value = input(q.format(default=default))
    if input_value == '':
        input_value = default

    try:
        input_value = int(input_value)
    except ValueError:
        print('Please enter integer id value')
    if len([d['id'] for d in devices if d['id'] == input_value]) == 0:
        print('Selected audio id value not on the list')
        sys.exit(1)
    return input_value


def load_config(config_filename):
    conf = {}
    if os.path.exists(config_filename):
        with open(config_filename) as f:
            conf = json.load(f)

    return conf


def outputq(out, queue):
    try:
        for line in iter(out.readline, b''):
            queue.put(line.strip())
    except ValueError:
        pass
    finally:
        out.close()


def process_handler(args, key, needles=None):
    global DO_EXIT
    if VERBOSE:
        print('Starting process', key)
        print('ARGS:', args)
    with subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, bufsize=1,
                          universal_newlines=True) as proc:

        q = queue.SimpleQueue()
        stdout_t = threading.Thread(target=outputq, args=(proc.stdout, q))
        stdout_t.daemon = True  # thread dies with the program
        stdout_t.start()

        st = time.time()
        missing_needles = needles
        while not DO_EXIT:
            time.sleep(0.1)
            now = time.time()
            status = proc.poll()

            if status is not None:
                if VERBOSE:
                    print('PROCESS RETURNED:', status, key)
                break

            while not q.empty():
                line = q.get(timeout=0.1)

                if VERBOSE:
                    print(line)

                if needles is not None:
                    new_missing_needles = []
                    for n in missing_needles:
                        if line.find(n) < 0:

                            new_missing_needles.append(n)
                        else:
                            if VERBOSE:
                                print('NEEDLE FOUND', key)
                    missing_needles = new_missing_needles

            MISSING_NEEDLES[key] = len(missing_needles)
            if now - st > 10.0 and len(missing_needles) > 0:
                if VERBOSE:
                    print('NEEDLE NOT FOUND FOR', key)
                proc.terminate()

        if DO_EXIT:
            if VERBOSE:
                print("EXIT COMMANDED TERMINATING", key)
            proc.terminate()


if __name__ == '__main__':
    config_file = os.path.join(os.getcwd(), 'launcher_config.json')
    config = load_config(config_file)

    (input_devices, output_devices) = audio.get_audio_devices()

    deftx = config.get('tx', None)
    defrx = config.get('rx', None)

    rx_device = device_input(input_devices, 'TX device [{default}]:', '### SELECT RADIO AUDIO OUTPUT DEVICE ###', defrx)
    tx_device = device_input(output_devices, 'RX device [{default}]:', '### SELECT RADIO AUDIO INPUT DEVICE ###', deftx)

    print('### SELECT HAMLIB COM PORT')
    ports = serial.tools.list_ports.comports()
    for p in ports:
        print(p)

    defcomport = config.get('com', None)
    comport = input(f'COM port (COMx) [{defcomport}]: ').strip().upper()
    if comport == '':
        comport = defcomport

    defcallsign = config.get('callsign', None)
    callsign = input(f'Callsign [{defcallsign}]: ').strip().upper()
    if callsign == '':
        callsign = defcallsign

    if not callsign.endswith('-0'):
        callsign = callsign.split('-')[0] + '-0'

    config = {
        'tx': tx_device,
        'rx': rx_device,
        'com': comport,
        'callsign': callsign
    }
    with open(config_file, 'w') as f:
        json.dump(config, f)

    processes = (
        {
            'key': 'hamlib',
            'cli': f'hamlib-w64-4.5.5\\bin\\rigctld.exe -m 3073 -r {comport} -s 19200 -vvvv',
            'needles': []
        },
        {
            'key': 'tnc',
            'cli': f'radiolink\\radiolink.exe --mycall {callsign} --tx {tx_device} --rx {rx_device} --port 3000 --radiocontrol rigctld --rigctld_port 4532 --rigctld_ip 127.0.0.1 --qrv --tx-audio-level 125 --rx-buffer-size 16',
            'needles': ['Starting TCP/IP socket', '[RIGCTLD] Connected PTT instance to rigctld']
        },
        {
            'key': 'optional',
            'cli': sys.argv[1] if len(sys.argv) > 1 else None,
            'needles': [sys.argv[2], ] if len(sys.argv) > 2 else []
        }
    )

    print('STARTING PROCESSES')

    process_threads = [
        threading.Thread(target=process_handler, args=[p['cli'], p['key'], p['needles']])
        for p in processes if p['cli'] is not None
    ]

    for t in process_threads:
        t.daemon = True
        t.start()

    all_running = True
    all_started = False
    while all_running:
        time.sleep(1)
        threads_isalive = [t.is_alive() for t in process_threads]
        if VERBOSE:
            print(datetime.datetime.now(), threads_isalive)
        if not all_started and all((MISSING_NEEDLES[k] == 0 for k in MISSING_NEEDLES)):
            print('ALL NEEDLES FOUND. EVERYTHING STARTED')
            print('GUI RUNNING AT http://localhost:8080')
            webbrowser.open_new('http://localhost:8080')
            all_started = True
        all_running = all(threads_isalive)

    print('SOME PROCESS DIED. TERMINATING ALL AND EXITING')
    DO_EXIT = True
    for t in process_threads:
        t.join(timeout=5)
