import argparse
import time
import pickle

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image


window_seconds = 10

def main():
    with Image.open("blank.png") as img:
        blank_img = np.asarray(img)

    with Image.open("fireball.png") as img:
        fireball_img = np.asarray(img)


    parser = argparse.ArgumentParser()
    # use docs to check which parameters are required for specific board, e.g. for Cyton - set serial port
    parser.add_argument('--timeout', type=int, help='timeout for device discovery or connection', required=False,
                        default=0)
    parser.add_argument('--ip-port', type=int, help='ip port', required=False, default=0)
    parser.add_argument('--ip-protocol', type=int, help='ip protocol, check IpProtocolType enum', required=False,
                        default=0)
    parser.add_argument('--ip-address', type=str, help='ip address', required=False, default='')
    parser.add_argument('--serial-port', type=str, help='serial port', required=False, default='')
    parser.add_argument('--mac-address', type=str, help='mac address', required=False, default='')
    parser.add_argument('--other-info', type=str, help='other info', required=False, default='')
    parser.add_argument('--serial-number', type=str, help='serial number', required=False, default='')
    parser.add_argument('--board-id', type=int, help='board id, check docs to get a list of supported boards',
                        required=True)
    parser.add_argument('--file', type=str, help='file', required=False, default='')
    parser.add_argument('--master-board', type=int, help='master board id for streaming and playback boards',
                        required=False, default=BoardIds.NO_BOARD)
    args = parser.parse_args()

    params = BrainFlowInputParams()
    params.ip_port = args.ip_port
    params.serial_port = args.serial_port
    params.mac_address = args.mac_address
    params.other_info = args.other_info
    params.serial_number = args.serial_number
    params.ip_address = args.ip_address
    params.ip_protocol = args.ip_protocol
    params.timeout = args.timeout
    params.file = args.file
    params.master_board = args.master_board

    board = BoardShim(args.board_id, params)

    sampling_rate = BoardShim.get_sampling_rate(args.board_id)
    sampling_size = sampling_rate * window_seconds

    record_data = {
        "board_id" : args.board_id,
        "window_seconds" : window_seconds,
        "intent_data" : [],
        "baseline_data" : []
    }

    board.prepare_session()
    board.start_stream()

    # 1. wait 5 seconds before starting
    wait_seconds = 2
    print("Get ready in {} seconds".format(wait_seconds))
    time.sleep(wait_seconds)

    input("Get ready to think about anything else. Press enter to continue")
    print("Be idle for {} seconds".format(3 * window_seconds))
    plt.imshow(blank_img)
    plt.draw()
    for i in range(3):
        plt.pause(window_seconds)
        baseline_data = board.get_current_board_data(sampling_size)
        record_data["baseline_data"].append(baseline_data)
    plt.close()

    for i in range(3):
        input("Get ready to think about fireballs. Press enter to continue")
        # 2. think push button 10 seconds, record
        print("Think push a button for {} seconds".format(window_seconds))
        # time.sleep(window_seconds)
        plt.imshow(fireball_img)
        plt.draw()
        plt.pause(window_seconds + 1) # skip the part where you press enter
        plt.close()

        intent_data = board.get_current_board_data(sampling_size)
        record_data["intent_data"].append(intent_data)

    board.stop_stream()
    board.release_session()

    # save record data
    print("Saving Data")
    with open('recorded_eeg.pkl', 'wb') as f:
        pickle.dump(record_data, f)

if __name__ == "__main__":
    main()