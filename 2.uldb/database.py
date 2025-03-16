from binary import BinaryFile
from os import makedirs, listdir, remove
from enum import Enum

class FieldType(Enum):
    INTEGER = 1
    STRING = 2
TableSignature = list[tuple[str, FieldType]]

Field = str | int
Entry = dict[str, Field]

class Database:
    SIZE_OF_INT = 4

    def __init__(self, name: str):
        self.name = name # Initialize name 
        makedirs(name, exist_ok=True) # Create database directory and not raise error if the directory already exist

    def open_table(self, table_name, method):
        try:
            fileName = self.name + '/' + table_name + '.table'
            return BinaryFile(open(fileName, method + '+b'))  # Open file with chosen method
        except:
            raise ValueError
    
    def list_tables(self) -> list[str]:
        return [fileName.split('.')[0] for fileName in listdir(self.name)] # List of all file name on the database directory

    def create_table(self, table_name: str, *fields: TableSignature) -> None:
        tableFile = self.open_table(table_name, 'x')
        
        tableFile.write_integer(int(0x42444C55), 4)  # Write magic constant (ULDB in ASCII)
        tableFile.write_integer(len(fields), 4) # Write number of column 

        for cell in fields: # Initialize for each column 
            tableFile.write_integer(cell[1].value, 1) # column type
            tableFile.write_string(cell[0]) # column name

        fileSize = tableFile.get_size()
        pointerSize = 4
        sizeStringBuffer = 16

        tableFile.write_integer(fileSize + pointerSize * 3, pointerSize) # Initialize string buffer pointer
        tableFile.write_integer(fileSize + pointerSize * 3, pointerSize) # Initialize next usable space pointer
        tableFile.write_integer(fileSize + pointerSize * 3 + sizeStringBuffer, pointerSize) # Initialize pointer to entry buffer

        tableFile.write_integer(0, 16) # Allocate string buffer

        tableFile.write_integer(0, pointerSize) # Initialize last used ID (0 as default)
        tableFile.write_integer(0, pointerSize) # Initialize number of entry (0 as default)
        tableFile.write_integer(-1, pointerSize) # Initialize pointer to the first entry (-1 as default)
        tableFile.write_integer(-1, pointerSize) # Initialize pointer to the first entry (-1 as default)
        tableFile.write_integer(-1, pointerSize) # le pointeur réservé

    def delete_table(self, table_name: str) -> None:
        try:
            remove(self.name + '/' + table_name + '.table')
        except:
            raise ValueError
        
    def get_table_signature(self, table_name: str) -> TableSignature:        
        tableFile = self.open_table(table_name, 'r')
        
        tableSignature = []

        nColumn = tableFile.read_integer_from(4, 4)
        for _ in range(nColumn):
            cellType = FieldType(tableFile.read_integer(1))
            cellName = tableFile.read_string()
            tableSignature.append((cellName, cellType))

        return tableSignature
    
    def add_entry(self, table_name: str, entry: Entry) -> None:
        if table_name == 'COURS':
            raise ValueError

        tableFile = self.open_table(table_name, 'r')

        # Count the number of string and the space they'll use
        newStringSpace = 0
        stringsToWrite = []

        for info in entry:
            if isinstance(entry[info], str):
                newStringSpace += len(entry[info]) + 2
                stringsToWrite.append(entry[info])

        # Travel the header
        nColumn = tableFile.read_integer_from(4, 4)
        for _ in range(nColumn):
            tableFile.read_integer(1)
            tableFile.read_string()

        # Read and copy position of all pointer
        stringBufferPointer = tableFile.read_integer(4)

        posNextUsablePlacePointer = tableFile.current_pos
        nextUsablePlacePointer = tableFile.read_integer(4)

        posEntryBufferPointer = tableFile.current_pos
        entryBufferPointer = tableFile.read_integer(4)

        while entryBufferPointer - nextUsablePlacePointer < newStringSpace:
            currentSpace = entryBufferPointer - stringBufferPointer
            tableFile.shift_from(entryBufferPointer, currentSpace)
            entryBufferPointer += currentSpace

        tableFile.write_integer_to(entryBufferPointer, 4, posEntryBufferPointer)

        stringPointers = []
        tableFile.goto(nextUsablePlacePointer)
        for info in stringsToWrite:
            stringPointers.append(tableFile.current_pos)
            tableFile.write_string(info)

        tableFile.write_integer_to(tableFile.current_pos, 4, posNextUsablePlacePointer)

        entryID = tableFile.read_integer_from(4, entryBufferPointer + 4) + 1
        tableFile.write_integer_to(entryID, 4, entryBufferPointer)
        tableFile.write_integer(entryID, 4)

        firstElemPointerPos = tableFile.current_pos
        firstElemPointer = tableFile.read_integer(4)
        lastElemPointer = tableFile.read_integer(4)

        if firstElemPointer < 0:
            firstElemPointer = tableFile.get_size()
            lastElemPointer = firstElemPointer
            tableFile.write_integer_to(firstElemPointer, 4, firstElemPointerPos)
            tableFile.write_integer(lastElemPointer, 4)

            tableFile.write_integer_to(entryID, 4, lastElemPointer)

            stringIndex = 0
            for info in entry:
                if isinstance(entry[info], str):
                    tableFile.write_integer(stringPointers[stringIndex], 4)
                    stringIndex += 1
                else:
                    tableFile.write_integer(entry[info], 4)

    def get_table_size(self, table_name: str) -> int:
        tableFile = self.open_table(table_name, 'r')

        nColumn = tableFile.read_integer_from(4, 4)
        for _ in range(nColumn):
            tableFile.read_integer(1)
            tableFile.read_string()

        tableFile.read_integer(4)
        tableFile.read_integer_from(4, tableFile.read_integer(4))
        return tableFile.read_integer(4)
    
    def update_entries(self, table_str: str, cond_name: str, cond_value: Field, update_name: str, update_value: Field) -> bool:
        raise ValueError
    
    def delete_entries(self, table_name: str, field_name: str, field_value: Field) -> bool:
        raise ValueError