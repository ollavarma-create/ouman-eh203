"""In-memory bench simulator; never opens a physical serial port."""
class SimulatedSerial:
    port = '/dev/simulated-eh203'

    def __init__(self, blocks):
        self.blocks = {int(k): bytes(v) for k,v in blocks.items()}
        self.factory = dict(self.blocks)
        self.pending = b''
        self.writes = []
        self.fault = None

    @classmethod
    def from_backups(cls, original, factory):
        from .backup import verify_file
        verify_file(original)
        verify_file(factory)
        def blocks(obj):
            return {int(k): bytes.fromhex(v['data']) for k,v in obj['records'].items() if v['status']=='accepted'}
        initial, defaults = blocks(original), blocks(factory)
        if initial.keys()!=defaults.keys() or initial[1][:9]!=defaults[1][:9]:
            raise ValueError('Incompatible fixture pair')
        sim=cls(initial)
        sim.factory=defaults
        return sim

    def reset_input_buffer(self):
        self.pending = b''

    def flush(self):
        pass

    def read(self, n):
        result, self.pending = self.pending[:n], self.pending[n:]
        return result

    def factory_reset(self):
        self.blocks = dict(self.factory)
        self.pending = b''

    def reboot(self):
        self.pending = b''
        self.fault = None

    @staticmethod
    def response(pid, data=b'', rejected=False):
        body = bytes((1,2,0,255)) if rejected else bytes((2,len(data)+2,0,pid))+data
        return bytes((2,))+body+bytes((sum(body)&255,))

    def write(self, tx):
        tx = bytes(tx)
        self.writes.append(tx)
        if len(tx)<6 or tx[0]!=2 or len(tx)!=tx[2]+4 or tx[3]!=0 or sum(tx[1:-1])&255!=tx[-1]:
            raise ValueError('Malformed request')
        op,pid,data=tx[1],tx[4],tx[5:-1]
        fault,self.fault=self.fault,None
        if fault=='reject':
            rx=self.response(pid,rejected=True)
        elif op==0x81 and not data and pid in self.blocks:
            rx=self.response(pid,self.blocks[pid])
        elif op==0x82 and self.apply(pid,data):
            rx=self.response(pid)
        else:
            rx=self.response(pid,rejected=True)
        if fault=='timeout':
            rx=b''
        elif fault=='checksum':
            rx=rx[:-1]+bytes((rx[-1]^1,))
        elif fault=='truncate':
            rx=rx[:-1]
        self.pending=rx
        return len(tx)

    def apply(self,pid,data):
        old=self.blocks.get(pid)
        if old is None or len(old)!=len(data):
            return False
        # Only observed dependency transitions; no claim of general firmware emulation.
        changes={i for i,(a,b) in enumerate(zip(old,data)) if a!=b}
        updated=dict(self.blocks)
        if pid in (65,66) and len(data)==31:
            if pid==65 and changes=={0} and old[0]==1 and data[0]==0 and updated[66][0]==1:
                updated[66]=bytes((0,))+updated[66][1:]
            elif old[0]==data[0]==0 and changes<=set(range(1,9)):
                mirror=12 if pid==65 else 14
                updated[mirror]=bytes(data[i] for i in (1,3,5))+updated[mirror][3:]
            else:
                return False
        elif pid==12 and changes=={20} and old[20]==5 and data[20]==15:
            b=bytearray(updated[14]); b[16]=15; updated[14]=bytes(b)
        elif pid==43 and old==bytes(2) and data==bytes((4,0)) and updated[17][17]==99:
            b=bytearray(updated[17]); b[17]=2; updated[17]=bytes(b)
        else:
            return False
        updated[pid]=data
        self.blocks=updated
        return True
