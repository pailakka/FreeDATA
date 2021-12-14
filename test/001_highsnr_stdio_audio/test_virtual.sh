#!/bin/bash -x
# Run a test using the virtual sound cards

function check_alsa_loopback {
    lsmod | grep snd_aloop >> /dev/null
    if [ $? -eq 1 ]; then
      echo "ALSA loopback device not present.  Please install with:"
      echo
      echo "  sudo modprobe snd-aloop index=1,2 enable=1,1 pcm_substreams=1,1 id=CHAT1,CHAT2"
      exit 1
    fi  
}

check_alsa_loopback

RX_LOG=$(mktemp)

# make sure all child processes are killed when we exit
trap 'jobs -p | xargs -r kill' EXIT

python3 test_rx.py --mode datac0 --frames 2 --bursts 1 --audiodev 4 --debug 2>&1 | tee ${RX_LOG} &
sleep 1
python3 test_tx.py --mode datac0 --frames 2 --bursts 1 --audiodev 5

tail -f ${RX_LOG} | sed '/RECEIVED BURSTS/ q'
