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

        # Shift the right amont of bytes to fit news strings
        shift = 0

        while entryBufferPointer - nextUsablePlacePointer < newStringSpace:
            currentSpace = entryBufferPointer - stringBufferPointer
            shift += currentSpace
            tableFile.shift_from(entryBufferPointer, currentSpace)
            entryBufferPointer += currentSpace

        # Update pointer of entry buffer by the shift amont 
        tableFile.write_integer_to(entryBufferPointer, 4, posEntryBufferPointer)

        # Write new strings to the string buffer
        stringPointers = []
        tableFile.goto(nextUsablePlacePointer)
        for info in stringsToWrite:
            stringPointers.append(tableFile.current_pos)
            tableFile.write_string(info)

        # Update pointer of the next usable space on the string buffer
        tableFile.write_integer_to(tableFile.current_pos, 4, posNextUsablePlacePointer)

        # Update number of entry and last ID used
        entryID = tableFile.read_integer_from(4, entryBufferPointer + 4) + 1
        tableFile.write_integer_to(entryID, 4, entryBufferPointer)
        tableFile.write_integer(entryID, 4)

        # Get pos and value of entry buffer header pointers
        posFirstEntryBufferPointer = tableFile.current_pos
        firstEntryBufferPointer = tableFile.read_integer(4)

        posLastEntryBufferPointer = tableFile.current_pos
        lastEntryBufferPointer = tableFile.read_integer(4)

        tableFile.read_integer(4) # This space'll be useful later

        if firstEntryBufferPointer < 0:
            # Set the entry buffer pointer for the first time. Both pointer point to the first and only entry
            firstEntryPointer = tableFile.current_pos
            tableFile.write_integer_to(firstEntryPointer, 4, posFirstEntryBufferPointer)
            tableFile.write_integer_to(firstEntryPointer, 4, posLastEntryBufferPointer)
        else:
            # Update first entry because of the shift and set last entry to the end of the file
            tableFile.write_integer_to(firstEntryBufferPointer + shift, 4, posFirstEntryBufferPointer)
            tableFile.write_integer_to(tableFile.get_size(), 4, posLastEntryBufferPointer)
            tableFile.write_integer_to(tableFile.get_size(), 4, tableFile.get_size() - 4)

        tableFile.write_integer_to(entryID, 4, tableFile.get_size())

        # Write int or reference of string to the string buffer
        stringIndex = 0
        for info in entry:
            if isinstance(entry[info], str):
                tableFile.write_integer(stringPointers[stringIndex], 4)
                stringIndex += 1
            else:
                tableFile.write_integer(entry[info], 4)

        if entryID == 1:
            tableFile.write_integer(-1, 4) # Write that there are no entry before the first one
        else:
            tableFile.write_integer(lastEntryBufferPointer + shift, 4)

        
        tableFile.write_integer(-1, 4) # Write that there are no entry after the last one 

    def get_complete_table(self, table_name: str) -> list[Entry]:
        tableFile = self.open_table(table_name, 'r')

        # Travel the header
        nColumn = tableFile.read_integer_from(4, 4)
        for _ in range(nColumn):
            tableFile.read_integer(1)
            tableFile.read_string()

        posEntryBuffer = tableFile.read_integer_from(4, tableFile.current_pos + 8)
        tableFile.read_integer_from(4, posEntryBuffer + 4)

        tableFile.goto(tableFile.read_integer(4))
        
        completeTable = []
        nextEntryPointer = 0
        
        while nextEntryPointer >= 0:
            currentEntry = {}

            currentEntry['id'] = tableFile.read_integer(4)

            for cell in self.get_table_signature(table_name):
                if cell[1] == FieldType.INTEGER:
                    currentEntry[cell[0]] = tableFile.read_integer(4)
                else:
                    stringPointer = tableFile.read_integer(4)
                    currentPos = tableFile.current_pos
                    currentEntry[cell[0]] = tableFile.read_string_from(stringPointer)
                    tableFile.goto(currentPos)

            nextEntryPointer = tableFile.read_integer_from(4, tableFile.current_pos + 4)
            completeTable.append(currentEntry)
        return completeTable
    
    def get_entry(self, table_name: str, field_name: str, field_value: Field) -> Entry | None:
        tableFile = self.open_table(table_name, 'r')
        
        # Get index of the fieldName
        fieldIndex = None
        
        nColumn = tableFile.read_integer_from(4, 4)

        for columnIndex in range(nColumn):
            currentFieldType = tableFile.read_integer(1)
            if tableFile.read_string() == field_name:
                fieldIndex = columnIndex
                fieldType = currentFieldType

        if fieldIndex == None:
            return None
        else:
            entryBufferPointer = tableFile.read_integer_from(4, tableFile.current_pos + 8)
            nextEntryPointer = tableFile.read_integer_from(4, entryBufferPointer + 8)
            tableFile.goto(nextEntryPointer)

            while nextEntryPointer > 0:
                fieldPointer = tableFile.current_pos + 4 * (fieldIndex + 1)
                fieldToTry = tableFile.read_integer_from(4, fieldPointer)
                
                if fieldType == 2:
                    fieldToTry = tableFile.read_string_from(fieldToTry)

                if fieldToTry == field_value:
                    return self.read_entry(table_name, nextEntryPointer)

                nextEntryPointerPos = fieldPointer + 4 * (nColumn - fieldIndex) + 4 # Get post of next entry pointer next to the previous entry pointer
                nextEntryPointer = tableFile.read_integer_from(4, nextEntryPointerPos) # Read next entry pointer by skipping last entry pointer

            return None
        
    def get_entries(self, table_name: str, field_name: str, field_value: Field) -> list[Entry]:
        tableFile = self.open_table(table_name, 'r')
        
        # Get index of the fieldName
        fieldIndex = None
        
        nColumn = tableFile.read_integer_from(4, 4)

        for columnIndex in range(nColumn):
            currentFieldType = tableFile.read_integer(1)
            if tableFile.read_string() == field_name:
                fieldIndex = columnIndex
                fieldType = currentFieldType

        if fieldIndex == None:
            return []
        else:
            data = []

            entryBufferPointer = tableFile.read_integer_from(4, tableFile.current_pos + 8)
            nextEntryPointer = tableFile.read_integer_from(4, entryBufferPointer + 8)
            tableFile.goto(nextEntryPointer)

            while nextEntryPointer > 0:
                fieldPointer = tableFile.current_pos + 4 * (fieldIndex + 1)
                fieldToTry = tableFile.read_integer_from(4, fieldPointer)
                
                if fieldType == 2:
                    fieldToTry = tableFile.read_string_from(fieldToTry)

                if fieldToTry == field_value:
                    data.append(self.read_entry(table_name, nextEntryPointer))

                nextEntryPointerPos = fieldPointer + 4 * (nColumn - fieldIndex) + 4 # Get post of next entry pointer next to the previous entry pointer
                nextEntryPointer = tableFile.read_integer_from(4, nextEntryPointerPos) # Read next entry pointer by skipping last entry pointer

            return data
                
    def read_entry(self, table_name, entryPointer):
        tableFile = self.open_table(table_name, 'r')

        tableFile.goto(entryPointer)
        entry = {}
        entry['id'] = tableFile.read_integer(4)
        for cellInfo in self.get_table_signature(table_name):
            if cellInfo[1] == FieldType.INTEGER:
                entry[cellInfo[0]] = tableFile.read_integer(4)
            else:
                stringPos = tableFile.read_integer(4)
                pos = tableFile.current_pos
                print(hex(stringPos), cellInfo[1], hex(pos - 4))
                entry[cellInfo[0]] = tableFile.read_string_from(stringPos)
                tableFile.goto(pos)
        return entry


    def get_table_size(self, table_name: str) -> int:
        tableFile = self.open_table(table_name, 'r')

        nColumn = tableFile.read_integer_from(4, 4)
        for _ in range(nColumn):
            tableFile.read_integer(1)
            tableFile.read_string()

        pointerNbEntry = tableFile.read_integer_from(4, tableFile.current_pos + 8) + 4
        return tableFile.read_integer_from(4, pointerNbEntry)
    
COURSES = [
    {'MNEMONIQUE': 101, 'NOM': 'Programmation',
     'COORDINATEUR': 'Thierry Massart', 'CREDITS': 10},
    {'MNEMONIQUE': 102, 'NOM': 'Fonctionnement des ordinateurs',
     'COORDINATEUR': 'Gilles Geeraerts', 'CREDITS': 5},
    {'MNEMONIQUE': 103, 'NOM': 'Algorithmique I',
     'COORDINATEUR': 'Olivier Markowitch', 'CREDITS': 10},
    {'MNEMONIQUE': 105, 'NOM': 'Langages de programmation I',
     'COORDINATEUR': 'Christophe Petit', 'CREDITS': 5},
    {'MNEMONIQUE': 106, 'NOM': 'Projet d\'informatique I',
     'COORDINATEUR': 'Gwenaël Joret', 'CREDITS': 5},
]

db = Database('programme')
db.create_table(
    'cours',
    ('MNEMONIQUE', FieldType.INTEGER),
    ('NOM', FieldType.STRING),
    ('COORDINATEUR', FieldType.STRING),
    ('CREDITS', FieldType.INTEGER)
)
db.add_entry('cours', COURSES[0])
db.add_entry('cours', COURSES[1])
db.add_entry('cours', COURSES[2])
db.add_entry('cours', COURSES[3])
db.add_entry('cours', COURSES[4])

# print(db.get_entries('cours', 'CREDITS', 10))