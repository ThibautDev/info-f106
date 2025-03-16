from typing import BinaryIO


class BinaryFile:
    def __init__(self, file: BinaryIO):
        self.__file = file # Define file as hidden for safety reasons 

    def goto(self, pos: int) -> None:
        self.__file.seek(pos)

    @property
    def current_pos(self) -> int:
        return self.__file.tell()
    
    def increment_int(self, n, size):
        currentPos = self.__file.tell()
        currentInt = self.read_integer(4)
        self.write_integer_to(currentInt + n, size, currentPos)

    def get_size(self) -> int:
        currentPos = self.current_pos
        self.__file.seek(0, 2)
        fileSize = self.current_pos
        self.__file.seek(currentPos)
        return  fileSize
    
    def write_integer(self, n: int, size: int) -> int:
        self.__file.write(n.to_bytes(size, byteorder='little', signed=True))

    def write_integer_to(self, n: int, size: int, pos: int) -> int:
        self.goto(pos)
        self.write_integer(n, size)

    def write_string(self, s: str) -> int:
        self.write_integer(len(s.encode('utf-8')), 2)
        self.__file.write(s.encode('utf-8'))

    def write_string_to(self, s: str, pos: int) -> int:
        self.goto(pos)
        self.write_string(s)


    def read_integer(self, size: int) -> int:
        return int.from_bytes(self.__file.read(size), byteorder='little', signed=True)

    def read_integer_from(self, size: int, pos: int) -> int:
        self.goto(pos)
        return self.read_integer(size)
    
    def read_string(self) -> str:
        stringSize = self.read_integer(2)
        return self.__file.read(stringSize).decode('utf-8')

    def read_string_from(self, pos: int) -> str:
        self.goto(pos)
        return self.read_string()
    
    def shift_from(self, pos, size):
        self.goto(pos)
        spaceToShift = self.get_size() - pos
        data = self.__file.read(spaceToShift)
        self.goto(pos)
        self.__file.write(b'\x00' * size)
        self.__file.write(data)