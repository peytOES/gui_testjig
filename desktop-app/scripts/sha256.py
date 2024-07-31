import hashlib
import sys
import os

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Usage: %s.py <filename>" % sys.argv[0])
        sys.exit(0)

    filename = sys.argv[1]
    contents = open(filename, 'rb')
    h = hashlib.sha256(contents.read()).hexdigest()
    contents.close()
    print('"filename": "%s",' % os.path.basename(filename))
    print('"sha256": "%s"' % h)
