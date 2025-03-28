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
        return self.__file.tell()
    
    def increment_int_from(self, n: int, size: int, pos: int):
        currentInt = self.read_integer_from(4, pos)
        if currentInt != -1: # Ignore unassigned int
            newInt = currentInt + n
            self.write_integer_to(newInt, size, pos)

            return newInt
        return currentInt

    def get_size(self) -> int:
        currentPos = self.current_pos
        self.__file.seek(0, 2)
        fileSize = self.current_pos
        self.__file.seek(currentPos)
        return  fileSize
    
    def write_integer(self, n: int, size: int) -> int:
        if n != None:
            self.__file.write(n.to_bytes(size, byteorder='little', signed=True))
        else:
            self.__file.seek(self.current_pos + size)

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

    def write_fields(self, db, table_name, strings_pointer, entry):
        for field in db.get_table_signature(table_name):
            fieldName = field[0]
            fieldType = repr(field[1])

            if fieldType == repr(FieldType.INTEGER):
                self.write_integer(entry[fieldName], 4)
            else:
                stringPointer = strings_pointer.pop(0)
                self.write_integer(stringPointer, 4)

    def analyse_entry(self, entrySignature, entry_pointer):
        entry = {}
        self.goto(entry_pointer)

        for field in entrySignature:
            fieldName = field[0]
            fieldType = repr(field[1])

            if fieldType == repr(FieldType.INTEGER):
                entry[fieldName] = self.read_integer(4)
            else:
                stringPointer = self.read_integer(4)
                currentPos = self.current_pos
                entry[fieldName] = self.read_string_from(stringPointer)
                self.goto(currentPos)
        self.skip(4)
        next_entry_pointer = self.read_integer(4)
        return entry, next_entry_pointer
            

    def skip(self, dist):
        self.goto(self.current_pos + dist)