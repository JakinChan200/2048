import ctypes
import os

dll_path = os.path.abspath("botLib.dll")
botLib = ctypes.CDLL(dll_path)

botLib.init_tables()

botLib.find_best_move.argtypes = [ctypes.c_uint64]

powerDict = {
    "" : 0,
    "2": 1,
    "4": 2,
    "8": 3,
    "16": 4,
    "32": 5,
    "64": 6,
    "128": 7,
    "256": 8,
    "512": 9,
    "1024": 10,
    "2048": 11,
    "4096": 12,
    "8192": 13,
    "16384": 14,
    "32768": 15
}

def to_c_board(m):
    board = 0
    i = 0
    for row in m:
        for c in row:
            board |= int(powerDict[c]) << (4*i)
            i += 1
    return board


#https://stackoverflow.com/questions/145270/calling-c-c-from-python
#https://github.com/nneonneo/2048-ai/blob/master/2048.py#L71
#https://stackoverflow.com/questions/5081875/ctypes-beginner
