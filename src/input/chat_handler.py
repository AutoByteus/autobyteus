import sys
import threading
import time
from colorama import Fore, Style


class ChatHandler:
    def __init__(self):
        self.waiting = False

    def print_waiting_message(self):
        counter = 0
        while self.waiting:
            counter += 1
            sys.stdout.write(Fore.YELLOW + f'\rWaiting for copied message... {counter}s' + Style.RESET_ALL)
            sys.stdout.flush()
            time.sleep(1)

    def start_waiting(self):
        self.waiting = True
        self.waiting_thread = threading.Thread(target=self.print_waiting_message)
        self.waiting_thread.start()

    def stop_waiting(self):
        self.waiting = False
        self.waiting_thread.join()
