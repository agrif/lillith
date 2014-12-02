from lillith import *
namespace = globals().copy()

if __name__ == '__main__':
    import sys
    import code
    import readline
    import argparse

    parse = argparse.ArgumentParser(description="an interactive lillith shell")
    config.add_arguments(parse)
    parse.parse_args()
    
    code.interact("lillith", local=namespace)
