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
        if table_name in self.list_tables() or method == 'x':
            try:
                fileName = self.name + '/' + table_name + '.table'
                return BinaryFile(open(fileName, method + '+b'))  # Open file with chosen method
            except:
                raise ValueError
        else:
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

        tableFile.write_integer(0, sizeStringBuffer) # Allocate string buffer

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
    
    def scan_strings_entry(self, entry: Entry) -> int:
        stringSpace = 0
        strings = []

        for info in entry:
            if isinstance(entry[info], str):
                stringSpace += len(entry[info]) + 2
                strings.append(entry[info])

        return stringSpace, strings
    
    def get_header_pointer(self, tableFile: BinaryFile):
        tableFile.read_integer_from(4, 4)
        nColumn = tableFile.read_integer_from(4, 4)

        for _ in range(nColumn):
            tableFile.read_integer(1)
            tableFile.read_string()

        return tableFile.current_pos
        
    def get_string_buffer_pointer(self, tableFile: BinaryFile):
        headerPointer = self.get_header_pointer(tableFile)
        stringBufferPointer = tableFile.read_integer_from(4, headerPointer)
        return stringBufferPointer
    
    def get_last_string_buffer_pointer(self, tableFile: BinaryFile):
        headerPointer = self.get_header_pointer(tableFile)
        lastEntryBufferPointer = tableFile.read_integer_from(4, headerPointer + 4)
        return lastEntryBufferPointer
    
    def update_last_string_buffer_pointer(self, tableFile: BinaryFile, shift: int):
        lastStringBufferPointer = self.get_last_string_buffer_pointer(tableFile)

        headerPointer = self.get_header_pointer(tableFile)
        lastStringBufferPointerPointer = headerPointer + 4

        newLastStringBufferPointer = lastStringBufferPointer + shift
        tableFile.write_integer_to(newLastStringBufferPointer, 4, lastStringBufferPointerPointer)

    def get_entry_buffer_pointer(self, tableFile: BinaryFile):
        headerPointer = self.get_header_pointer(tableFile)
        entryBufferPointer = tableFile.read_integer_from(4, headerPointer + 8)
        return entryBufferPointer
    
    def update_entry_buffer_pointer(self, tableFile: BinaryFile, shift: int):
        entryBufferPointer = self.get_entry_buffer_pointer(tableFile)

        headerPointer = self.get_header_pointer(tableFile)
        entryBufferPointerPointer = headerPointer + 8

        newEntryBufferPointer = entryBufferPointer + shift
        tableFile.write_integer_to(newEntryBufferPointer, 4, entryBufferPointerPointer)
    
    def get_string_buffer_space(self, tableFile: BinaryFile):
        stringBufferPointer = self.get_string_buffer_pointer(tableFile)
        entryBufferPointer = self.get_entry_buffer_pointer(tableFile)
        stringBufferSpace = entryBufferPointer - stringBufferPointer
        return stringBufferSpace
    
    def get_string_buffer_used_spaces(self, tableFile: BinaryFile):
        stringBufferPointer = self.get_string_buffer_pointer(tableFile)
        lastStringBufferPointer = self.get_last_string_buffer_pointer(tableFile)
        stringBufferUsedSpace = lastStringBufferPointer - stringBufferPointer
        return stringBufferUsedSpace
    
    def get_string_buffer_shift(self, tableFile: BinaryFile, space: int):
        stringBufferSpace = self.get_string_buffer_space(tableFile)
        stringBufferUsedSpace = self.get_string_buffer_used_spaces(tableFile)
        newStringBufferSpace = stringBufferSpace

        while newStringBufferSpace < stringBufferUsedSpace + space:
            newStringBufferSpace *= 2

        shift = newStringBufferSpace - stringBufferSpace
        return shift
            
    def upgrade_string_buffer(self, tableFile: BinaryFile, shift):
        lastEntryBufferPointer = self.get_last_string_buffer_pointer(tableFile)
        tableFile.shift_from(lastEntryBufferPointer, shift)
        self.update_entry_buffer_pointer(tableFile, shift)

    def insert_string(self, tableFile: BinaryFile, entry: Entry) -> list[int]:
        spaceEntryString, entryString = self.scan_strings_entry(entry)
        lastEntryBufferPointer = self.get_last_string_buffer_pointer(tableFile)

        stringsPointer = []

        tableFile.goto(lastEntryBufferPointer)
        for currentString in entryString:
            stringsPointer.append(tableFile.current_pos)
            tableFile.write_string(currentString)

        self.update_last_string_buffer_pointer(tableFile, spaceEntryString)

        return stringsPointer

    def get_nb_entry_pointer(self, tableFile: BinaryFile):
        entryBufferPointer = self.get_entry_buffer_pointer(tableFile)
        nbEntryPointer = entryBufferPointer + 4
        return nbEntryPointer
    
    def get_first_entry_pointer_pointer(self, tableFile: BinaryFile):
        entryBufferPointer = self.get_entry_buffer_pointer(tableFile)
        firstEntryPointerPointer = entryBufferPointer + 8
        return firstEntryPointerPointer
    
    def get_first_entry_pointer(self, tableFile: BinaryFile):
        firstEntryPointerPointer = self.get_first_entry_pointer_pointer(tableFile)
        firstEntryPointer = tableFile.read_integer_from(4, firstEntryPointerPointer)
        return firstEntryPointer
    
    def get_last_entry_pointer_pointer(self, tableFile: BinaryFile):
        entryBufferPointer = self.get_entry_buffer_pointer(tableFile)
        lastEntryPointerPointer = entryBufferPointer + 12
        return lastEntryPointerPointer
    
    def update_entrys_pointers(self, tableFile: BinaryFile, shift: int, entry):
        lastIdUsedPointer = self.get_entry_buffer_pointer(tableFile)
        nbEntryPointer = self.get_nb_entry_pointer(tableFile)

        nbEntry = tableFile.read_integer_from(4, nbEntryPointer)
        newEntryId = nbEntry + 1

        # Update entry buffer header pointers
        tableFile.write_integer_to(newEntryId, 4, lastIdUsedPointer)
        tableFile.write_integer_to(newEntryId, 4, nbEntryPointer)

        NbEntry = tableFile.read_integer_from(4, nbEntryPointer)

        firstEntryPointerPointer = self.get_first_entry_pointer_pointer(tableFile)
        lastEntryPointerPointer = self.get_last_entry_pointer_pointer(tableFile)

        if NbEntry == 1:
            firstEntryPointer = tableFile.get_size()
        else:
            firstEntryPointer = tableFile.read_integer_from(4, firstEntryPointerPointer) + shift
            sizeOfEntry = (1 + len(entry)) * 4

            tableFile.goto(firstEntryPointer)
            for entryIndex in range(nbEntry):
                startOfEntry = tableFile.current_pos

                lastEntryPointerToUpgradePointer = startOfEntry + sizeOfEntry
                nextEntryPointerToUpgradePointer = startOfEntry + sizeOfEntry + 4

                lastEntryPointerToUpgrade = tableFile.read_integer_from(4, lastEntryPointerToUpgradePointer)
                nextEntryPointerToUpgrade = tableFile.read_integer_from(4, nextEntryPointerToUpgradePointer)

                if lastEntryPointerToUpgrade > 0:
                    shiftedLastEntryPointerToUpgrade = lastEntryPointerToUpgrade + shift
                    tableFile.write_integer_to(shiftedLastEntryPointerToUpgrade, 4, lastEntryPointerToUpgradePointer)
                elif entryIndex == 1:
                    shiftedLastEntryPointerToUpgrade = -1
                    tableFile.write_integer_to(shiftedLastEntryPointerToUpgrade, 4, lastEntryPointerToUpgradePointer)
                
                if nextEntryPointerToUpgrade > 0:
                    shiftedNextEntryPointerToUpgrade = nextEntryPointerToUpgrade + shift
                else:
                    shiftedNextEntryPointerToUpgrade = nextEntryPointerToUpgradePointer + 4

                tableFile.write_integer_to(shiftedNextEntryPointerToUpgrade, 4, nextEntryPointerToUpgradePointer)

        lastEntryPointer = tableFile.get_size()

        tableFile.write_integer_to(firstEntryPointer, 4, firstEntryPointerPointer)
        tableFile.write_integer_to(lastEntryPointer, 4, lastEntryPointerPointer)

        return newEntryId


    def insert_entry(self, tableFile: BinaryFile, entry: Entry, newEntryId, stringsPointerList: list[int], table_name):
        entryPointer = tableFile.get_size()
        tableFile.write_integer_to(newEntryId, 4, entryPointer)
        
        for fieldInfo in self.get_table_signature(table_name):
            fieldName = fieldInfo[0]
            fieldType = fieldInfo[1]

            if fieldType == FieldType.INTEGER:
                tableFile.write_integer(entry[fieldName], 4)
            else:
                stringPointer = stringsPointerList.pop(0)
                tableFile.write_integer(stringPointer, 4)

        if newEntryId == 1:
            lastEntryPointer = -1
        else:
            endEntryPointer = tableFile.get_size() + 8
            entrySize = endEntryPointer - entryPointer

            lastEntryPointer = entryPointer - entrySize
        nextEntryPointer = -1

        tableFile.write_integer(lastEntryPointer, 4)
        tableFile.write_integer(nextEntryPointer, 4)

    def add_entry(self, table_name: str, entry: Entry) -> None:
        tableFile = self.open_table(table_name, 'r')

        spaceEntryString, entryString = self.scan_strings_entry(entry)

        shift = self.get_string_buffer_shift(tableFile, spaceEntryString)
        self.upgrade_string_buffer(tableFile, shift)
        stringsPointer = self.insert_string(tableFile, entry)

        newEntryId = self.update_entrys_pointers(tableFile, shift, entry)
        self.insert_entry(tableFile, entry, newEntryId, stringsPointer, table_name)

    def analyse_field(self, tableFile: BinaryFile, entryPointer, entrySignature):
        tableFile.goto(entryPointer)
        entry = {}

        for entryInfo in entrySignature:
            fieldName = entryInfo[0]
            fieldType = entryInfo[1]
            
            currentField = tableFile.read_integer(4)

            if fieldType == FieldType.STRING:
                fieldPos = tableFile.current_pos
                currentField = tableFile.read_string_from(currentField)
                tableFile.goto(fieldPos)

            entry[fieldName] = currentField

        nextEntryPointerPointer = tableFile.current_pos + 4
        nextEntryPointer = tableFile.read_integer_from(4, nextEntryPointerPointer)

        return entry, nextEntryPointer
    
    def analyse_field_selectively(self, tableFile: BinaryFile, entryPointer, nextEntryOffset, fieldInfo: list[tuple[int, Field]]):
        tableFile.goto(entryPointer)
        entry = []

        for offset, fieldType in fieldInfo:
            fieldPointer = entryPointer + offset
            field = tableFile.read_integer_from(4, fieldPointer)

            if fieldType == FieldType.STRING:
                fieldPos = tableFile.current_pos
                field = tableFile.read_string_from(field)
                tableFile.goto(fieldPos)

            entry.append(field)

        nextEntryPointerPointer = entryPointer + nextEntryOffset
        nextEntryPointer = tableFile.read_integer_from(4, nextEntryPointerPointer)

        return tuple(entry), nextEntryPointer


    def get_complete_table(self, table_name: str) -> list[Entry]:
        tableFile = self.open_table(table_name, 'r')
        
        completeTable = []
        entrySignature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        nextEntryPointer = self.get_first_entry_pointer(tableFile)

        while nextEntryPointer > 0:
            entry, nextEntryPointer = self.analyse_field(tableFile, nextEntryPointer, entrySignature)
            completeTable.append(entry)
        
        return completeTable
    
    def get_entry(self, table_name: str, field_name: str, field_value: Field) -> Entry | None:
        tableFile = self.open_table(table_name, 'r')
        
        entrySignature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        nextEntryPointer = self.get_first_entry_pointer(tableFile)

        while nextEntryPointer > 0:
            entry, nextEntryPointer = self.analyse_field(tableFile, nextEntryPointer, entrySignature)
            if entry[field_name] == field_value:
                return entry
        
        return None
    
    def get_entries(self, table_name: str, field_name: str, field_value: Field) -> list[Entry]:
        tableFile = self.open_table(table_name, 'r')
        
        entries = []
        entrySignature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        nextEntryPointer = self.get_first_entry_pointer(tableFile)

        while nextEntryPointer > 0:
            entry, nextEntryPointer = self.analyse_field(tableFile, nextEntryPointer, entrySignature)
            if entry[field_name] == field_value:
                entries.append(entry)
        
        return entries
    
    def analyseFieldSelection(self, entrySignature, fields, field_name):
        fieldToCheck = None
        fieldToGet = []

        for index, fieldInfo in enumerate(entrySignature):
            offset = index * 4
            currentFieldName = fieldInfo[0]
            currentFieldType = fieldInfo[1]

            if currentFieldName == field_name:
                fieldToCheck = (offset, currentFieldType)
            
            if currentFieldName in fields:
                fieldToGet.append((offset, currentFieldType))
        
        return fieldToCheck, fieldToGet
    
    def select_entry(self, table_name: str, fields: tuple[str], field_name: str, field_value: Field) -> Field | tuple[Field]:
        tableFile = self.open_table(table_name, 'r')
        
        entrySignature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)

        nextEntryOffset = (len(entrySignature) + 1) * 4
        nextEntryPointer = self.get_first_entry_pointer(tableFile)

        fieldToCheck, fieldToGet = self.analyseFieldSelection(entrySignature, fields, field_name)

        while nextEntryPointer > 0:
            currentEntryPointer  = nextEntryPointer
            field, nextEntryPointer = self.analyse_field_selectively(tableFile, currentEntryPointer, nextEntryOffset, [fieldToCheck])
            if field[0] == field_value:
                entry, _ = self.analyse_field_selectively(tableFile, currentEntryPointer, nextEntryOffset, fieldToGet)
                return entry

        return None
    
    def select_entries(self, table: str, fields: tuple[str], field_name: str, field_value: Field) -> list[Field | tuple[Field]]:
        tableFile = self.open_table(table, 'r')
        
        entrySignature = [('id', FieldType.INTEGER)] + self.get_table_signature(table)

        nextEntryOffset = (len(entrySignature) + 1) * 4
        nextEntryPointer = self.get_first_entry_pointer(tableFile)

        fieldToCheck, fieldToGet = self.analyseFieldSelection(entrySignature, fields, field_name)
        entries = []

        while nextEntryPointer > 0:
            currentEntryPointer  = nextEntryPointer
            field, nextEntryPointer = self.analyse_field_selectively(tableFile, currentEntryPointer, nextEntryOffset, [fieldToCheck])
            if field[0] == field_value:
                entry, _ = self.analyse_field_selectively(tableFile, currentEntryPointer, nextEntryOffset, fieldToGet)
                entries.append(entry)

        return entries
    
    def get_table_size(self, table_name: str) -> int:
        tableFile = self.open_table(table_name, 'r')

        nbEntryPointer = self.get_nb_entry_pointer(tableFile)
        nbEntry = tableFile.read_integer_from(4, nbEntryPointer)

        return nbEntry
        

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

possibles = {
    (102, 'Fonctionnement des ordinateurs'),
    (105, 'Langages de programmation I'),
    (106, 'Projet d\'informatique I')
}

print(db.select_entry('cours', ('MNEMONIQUE', 'NOM'), 'CREDITS', 5))