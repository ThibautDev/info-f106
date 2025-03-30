from typing import BinaryIO
from enum import Enum

class FieldType(Enum):
    INTEGER = 1
    STRING = 2

TableSignature = list[tuple[str, FieldType]]
Field = str | int
Entry = dict[str, Field]

class BinaryFile:
    def __init__(self, file: BinaryIO):
        self.__file = file # Define file as hidden for safety reasons 

    def goto(self, pos: int) -> None:
        self.__file.seek(pos)

    @property
    def current_pos(self) -> int:
        '''Get the current pos by using tell()'''
        return self.__file.tell()
    
    def increment_int_from(self, n: int, size: int, pos: int):
        '''Increment an int by the given amont'''
        currentInt = self.read_integer_from(4, pos)
        if currentInt != -1: # Ignore unassigned int
            newInt = currentInt + n
            self.write_integer_to(newInt, size, pos)

            return newInt
        return currentInt

    def get_size(self) -> int:
        '''Get the size of a file'''
        currentPos = self.current_pos
        self.__file.seek(0, 2)
        fileSize = self.current_pos
        self.__file.seek(currentPos)
        return  fileSize
    
    def write_integer(self, n: int, size: int) -> int:
        '''Write an unsigned integer in reversed byte order to the current position'''
        self.__file.write(n.to_bytes(size, byteorder='little', signed=True))

    def write_integer_to(self, n: int, size: int, pos: int) -> int:
        '''Write an unsigned integer in reversed byte order to a given position'''
        self.goto(pos)
        self.write_integer(n, size)

    def write_string(self, s: str) -> int:
        '''Write a string in utf-8 to the current position'''
        self.write_integer(len(s.encode('utf-8')), 2)
        self.__file.write(s.encode('utf-8'))

    def write_string_to(self, s: str, pos: int) -> int:
        '''Write a string in utf-8 to a given position'''
        self.goto(pos)
        self.write_string(s)

    def read_integer(self, size: int) -> int:
        '''Read an unsigned integer in reversed byte order from the current position'''
        return int.from_bytes(self.__file.read(size), byteorder='little', signed=True)

    def read_integer_from(self, size: int, pos: int) -> int:
        '''Read an unsigned integer in reversed byte order from a given position'''
        self.goto(pos)
        return self.read_integer(size)
    
    def read_string(self) -> str:
        '''Read a string in utf-8 from the current position'''
        stringSize = self.read_integer(2)
        return self.__file.read(stringSize).decode('utf-8')

    def read_string_from(self, pos: int) -> str:
        '''Read a string in utf-8 from the a given position'''
        self.goto(pos)
        return self.read_string()
    
    def shift_from(self, pos, size):
        '''Insert nul bits from a given position and push all data'''
        self.goto(pos)
        spaceToShift = self.get_size() - pos
        data = self.__file.read(spaceToShift)
        self.goto(pos)
        self.__file.write(b'\x00' * size)
        self.__file.write(data)