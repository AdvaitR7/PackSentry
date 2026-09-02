from schemas import ScanSession

class Printer:
    
    def print_session(self, session : ScanSession):
        print(f"session id = {session.scan_id}\ncapture time = {session.capture_time}\nmode = {session.scan_mode}")