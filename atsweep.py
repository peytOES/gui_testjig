import serial, time
def try_one(baud, kwargs):
    try:
        s = serial.Serial('COM13', baud, timeout=1, **kwargs)
        s.dtr = True
        # If we passed rtscts=True, .rts setting is managed by driver; otherwise assert it.
        if not kwargs.get('rtscts', False):
            s.rts = True
        time.sleep(0.3)
        s.reset_input_buffer()
        s.write(b'AT\r')
        time.sleep(0.6)
        resp = s.read_all()
        s.close()
        return repr(resp)
    except Exception as e:
        return f'ERR: {e!r}'

for rtscts in (False, True):
    print(f'=== rtscts={rtscts} ===')
    for b in (9600,19200,38400,57600,115200,230400):
        print(b, '->', try_one(b, {"rtscts": rtscts}))
