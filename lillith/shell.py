from lillith import *
namespace = globals().copy()

if __name__ == '__main__':
    import sys
    import code
    import readline
    try:
        _, dbpath, charname = sys.argv
    except ValueError:
        print("usage: {} <dbpath> <charname>".format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
        
    initialize(dbpath, charname, None, None)
    code.interact("lillith", local=namespace)
