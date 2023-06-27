import os
import sys

import serial.tools.list_ports

import audio

os.chdir('C:\\Temp\\mpkhfjo')


def device_input(devices, header):
    print(header)
    for d in devices:
        print(f'{d["id"]}: {d["name"]}')
    input_value = input("device idx: ")
    try:
        input_value = int(input_value)
    except ValueError:
        print('Please enter integer id value')
    if len([d['id'] for d in devices if d['id'] == input_value]) == 0:
        print('Selected audio id value not on the list')
        sys.exit(1)
    return input_value


if __name__ == '__main__':
    (input_devices, output_devices) = audio.get_audio_devices()
    tx_device = device_input(output_devices, '### SELECT RADIO AUDIO OUTPUT DEVICE ###')
    rx_device = device_input(input_devices, '### SELECT RADIO AUDIO INPUT DEVICE ###')

    print('### SELECT HAMLIB COM PORT')
    ports = serial.tools.list_ports.comports()
    for p in ports:
        print(p)
    comport = input('COM port (COMx): ').strip()

    callsign = input('Callsign: ').upper()

    hamlib_cli = f'hamlib-w64-4.5.5\\bin\\rigctld.exe -m 3073 -r {comport} -s 19200 -vvv'
    tnc_cli = f'tnc\\freedata-tnc.exe --mycall {callsign} --tx {tx_device} --rx {rx_device} --port 3000 --radiocontrol rigctld --rigctld_port 4532 --rigctld_ip 127.0.0.1 --qrv --tx-audio-level 125 --rx-buffer-size 16'
    optional_cli = sys.argv[1] if len(sys.argv) > 1 else None

    print(f'start /d {os.getcwd()} cmd /c {hamlib_cli}')
    os.system(f'start /d {os.getcwd()} cmd /c {hamlib_cli}')

    print(f'start /d {os.getcwd()} cmd /c {tnc_cli}')
    os.system(f'start /d {os.getcwd()} cmd /c {tnc_cli}')

    if optional_cli:
        print(f'start /d {os.getcwd()} cmd /c {optional_cli}')
        os.system(f'start /d {os.getcwd()} cmd /c {optional_cli}')
