import hashlib
import sys
import os

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Usage: cycloid_md5sum.py <filename>")
        sys.exit(0)

    filename = sys.argv[1]
    contents = open(filename, 'rb')
    h = hashlib.md5(contents.read()).hexdigest()
    contents.close()
    print('"filename": "%s",' % os.path.basename(filename))
    print('"md5": "%s"' % h)
