from typing import BinaryIO
import os


class BinaryFile:
    def __init__(self, file: BinaryIO):
        self.file = file

    def goto(self, pos: int) -> None:
        self.file.seek(pos)

    def get_size(self) -> int:
        currentPos = self.file.tell()
        self.file.seek(0, os.SEEK_END)
        fileSize = self.file.tell()
        self.file.seek(currentPos)
        return  fileSize
    
    def write_integer(self, n: int, size: int) -> int:
        self.file.write(n.to_bytes(size, byteorder='little'))

    def write_integer_to(self, n: int, size: int, pos: int) -> int:
        self.goto(pos)
        self.file.write(n.to_bytes(size))

    def write_string(self, s: str) -> int:
        self.write_integer(len(s.encode('utf-8')), 2)
        self.file.write(s.encode('utf-8'))

    def write_string_to(self, s: str, pos: int) -> int:
        self.goto(pos)
        self.write_string(s)


    def read_integer(self, size: int) -> int:
        return int.from_bytes(self.file.read(size), byteorder='little', signed=True)

    def read_integer_from(self, size: int, pos: int) -> int:
        self.goto(pos)
        return self.read_integer(size)
    
    def read_string(self) -> str:
        stringSize = self.read_integer(2)
        return self.file.read(stringSize).decode('utf-8')

    def read_string_from(self, pos: int) -> str:
        self.goto(pos)
        return self.read_string()