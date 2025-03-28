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

    def size_of_int(self, nb_int):
        return nb_int * 4

    def list_tables(self) -> list[str]:
        '''
        List of all file name on the database directory without the extentions
        '''

        return [fileName.split('.')[0] for fileName in listdir(self.name)]

    def open_table(self, table_name, method):
        '''
        Open table file if the file exist and or if we want to create a new file
        '''

        if table_name in self.list_tables() or method == 'x':
            try:
                fileName = self.name + '/' + table_name + '.table'
                return BinaryFile(open(fileName, method + '+b'))  # Open file with chosen method
            except:
                raise ValueError
        else:
            raise ValueError
            
    def create_table(self, table_name: str, *fields: TableSignature) -> None:
        '''
        Create a empty table file with all defaults header / pointer
        '''

        pointer_size = self.size_of_int(1) # For readability
        table_file = self.open_table(table_name, 'x')
        
        table_file.write_integer(int(0x42444C55), 4)  # Write magic constant (ULDB in ASCII)
        table_file.write_integer(len(fields), 4) # Write number of column 

        for field in fields: # Initialize for each column 
            table_file.write_integer(field[1].value, 1) # Field type
            table_file.write_string(field[0]) # Field name

        file_size = table_file.get_size()
        sizeStringBuffer = 16

        table_file.write_integer(file_size + pointer_size * 3, pointer_size) # Initialize string buffer pointer
        table_file.write_integer(file_size + pointer_size * 3, pointer_size) # Initialize next usable space pointer
        table_file.write_integer(file_size + pointer_size * 3 + sizeStringBuffer, pointer_size) # Initialize pointer to entry buffer header

        table_file.write_integer(0, sizeStringBuffer) # Allocate string buffer

        table_file.write_integer(0, pointer_size) # Initialize last used ID (0 as default)
        table_file.write_integer(0, pointer_size) # Initialize number of entry (0 as default)
        table_file.write_integer(-1, pointer_size) # Initialize pointer to the first entry (-1 as default)
        table_file.write_integer(-1, pointer_size) # Initialize pointer to the first entry (-1 as default)
        table_file.write_integer(-1, pointer_size) # Initialize pointer to the first 

    def delete_table(self, table_name: str) -> None:
        '''
        Delete table file if it exist
        '''

        try:
            remove(self.name + '/' + table_name + '.table')
        except:
            raise ValueError
        
    def get_string_header_pointer(self, tableFile: BinaryFile):
        nColumn = tableFile.read_integer_from(self.size_of_int(1), 4)

        for _ in range(nColumn):
            tableFile.read_integer(1)
            tableFile.read_string()

        return tableFile.current_pos
    
    def get_pointer(self, tableFile: BinaryFile, pointers_name: str | list[str]):
        '''
        Powerfull fonction that can give any pointer of the database
        '''
        
        # Get headers pointers
        string_header_pointer = self.get_string_header_pointer(tableFile)
        entry_header_pointer = tableFile.read_integer_from(self.size_of_int(1), string_header_pointer + 8)

        # Define all pointer pos
        pointers = {
            'first_string': string_header_pointer + self.size_of_int(0),
            'free_string_space': string_header_pointer + self.size_of_int(1),
            'entry_buffer': string_header_pointer + self.size_of_int(2),

            'last_id': entry_header_pointer + self.size_of_int(0),
            'nb_entry': entry_header_pointer + self.size_of_int(1),
            'first_entry': entry_header_pointer + self.size_of_int(2),
            'last_entry': entry_header_pointer + self.size_of_int(3),
            'first_deleted_entry': entry_header_pointer + self.size_of_int(4),
        }

        if isinstance(pointers_name, str):
            return pointers[pointers_name]
        else:
            return [pointers[name] for name in pointers_name]
        
    def get(self, tableFile: BinaryFile, pointers_name: str | list[str]):
        pointers = self.get_pointer(tableFile, pointers_name)

        if isinstance(pointers_name, str):
            return tableFile.read_integer_from(self.size_of_int(1), pointers)
        else:
            return [tableFile.read_integer_from(self.size_of_int(1), pointer) for pointer in pointers]
    
    def get_table_signature(self, table_name: str) -> TableSignature:        
        tableFile = self.open_table(table_name, 'r')
        
        tableSignature = []

        nColumn = tableFile.read_integer_from(self.size_of_int(1), 4)
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
    
    def get_string_buffer_shift(self, tableFile: BinaryFile, space: int):
        stringBufferPointer, freeSpaceStringBufferPointer, entryBufferPointer = self.get(tableFile, ['first_string', 'free_string_space', 'entry_buffer'])

        # Calculate spaces
        stringBufferSpace = entryBufferPointer - stringBufferPointer
        stringBufferUsedSpace = freeSpaceStringBufferPointer - stringBufferPointer

        # Aprox by power of 2 the new sting buffer space
        newStringBufferSpace = stringBufferSpace

        while newStringBufferSpace < stringBufferUsedSpace + space:
            newStringBufferSpace *= 2

        # Calculate the shift 
        shift = newStringBufferSpace - stringBufferSpace
        return shift
     
    def upgrade_string_buffer(self, tableFile: BinaryFile, shift):
        freeSpaceStringBufferPointerPointer, entry_buffer_pointer  = self.get_pointer(tableFile, ['free_string_space', 'entry_buffer'])
        freeSpaceStringBufferPointer = tableFile.read_integer_from(self.size_of_int(1), freeSpaceStringBufferPointerPointer)
        tableFile.shift_from(freeSpaceStringBufferPointer, shift)
        tableFile.increment_int_from(shift, self.size_of_int(1), entry_buffer_pointer)
        
    def upgrade_entry_buffer(self, tableFile: BinaryFile, table_name, shift):
        pointersToShift = self.get_pointer(tableFile, ['first_entry', 'last_entry', 'first_deleted_entry'])

        for pointer in pointersToShift:
            tableFile.increment_int_from(shift, 4, pointer)

        nb_id = self.get(tableFile, 'last_id')
        last_entry_pointer_offset =  self.size_of_int(1 + len(self.get_table_signature(table_name)))
        next_entry_pointer_offset = self.size_of_int(2 + len(self.get_table_signature(table_name)))

        entry_pointer, deleted_entry_pointer = self.get(tableFile, ['first_entry', 'first_deleted_entry'])

        while entry_pointer > 0:
            tableFile.increment_int_from(shift, self.size_of_int(1), entry_pointer + last_entry_pointer_offset)
            tableFile.increment_int_from(shift, self.size_of_int(1), entry_pointer + next_entry_pointer_offset)
            entry_pointer = tableFile.read_integer_from(4, entry_pointer + next_entry_pointer_offset)

        while deleted_entry_pointer > 0:
            tableFile.increment_int_from(shift, self.size_of_int(1), deleted_entry_pointer + last_entry_pointer_offset)
            tableFile.increment_int_from(shift, self.size_of_int(1), deleted_entry_pointer + next_entry_pointer_offset)
            entry_pointer = tableFile.read_integer_from(4, deleted_entry_pointer + next_entry_pointer_offset)

    def upgrade_db(self, tableFile, table_name, space):
        shift = self.get_string_buffer_shift(tableFile, space)
        self.upgrade_string_buffer(tableFile, shift)
        self.upgrade_entry_buffer(tableFile, table_name, shift)

    def insert_strings(self, tableFile: BinaryFile, entry_string: list[str], string_space) -> list[int]:
        free_string_space_pointer = self.get(tableFile, 'free_string_space')
        strings_pointer = []

        tableFile.goto(free_string_space_pointer)
        for string in entry_string:
            strings_pointer.append(tableFile.current_pos)
            tableFile.write_string(string)

        free_string_space_pointer_pointer = self.get_pointer(tableFile, 'free_string_space')
        tableFile.increment_int_from(string_space, 4, free_string_space_pointer_pointer)

        return strings_pointer
    
    def get_new_entry_pointer(self, tableFile: BinaryFile, table_signature):
        last_entry_pointer, first_deleted_entry_pointer = self.get(tableFile, ['last_entry', 'first_deleted_entry'])

        if first_deleted_entry_pointer > 0:
            entry_pointer = first_deleted_entry_pointer

        elif last_entry_pointer > 0:
            entry_pointer = tableFile.get_size()

            last_entry_pointer_pointer = self.get_pointer(tableFile, 'last_entry')

            next_entry_pointer_offset = self.size_of_int(len(table_signature) + 1)
            last_entry_next_entry_pointer_pointer = last_entry_pointer + next_entry_pointer_offset

            tableFile.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_pointer_pointer)
            tableFile.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_next_entry_pointer_pointer)
        else:
            first_entry_pointer_pointer, last_entry_pointer_pointer = self.get_pointer(tableFile, ['first_entry', 'last_entry'])
            entry_pointer = tableFile.get_size()
            tableFile.write_integer_to(entry_pointer, self.size_of_int(1), first_entry_pointer_pointer)
            tableFile.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_pointer_pointer)

        return entry_pointer, last_entry_pointer, -1
    
    def increment_id(self, tableFile: BinaryFile):
        last_id_pointer, nb_entry_pointer = self.get_pointer(tableFile, ['last_id', 'nb_entry'])

        tableFile.increment_int_from(1, self.size_of_int(1), last_id_pointer)
        tableFile.increment_int_from(1, self.size_of_int(1), nb_entry_pointer)

        new_id = self.get(tableFile, 'last_id')
        return new_id
    
    def add_entry(self, table_name: str, entry: Entry) -> None:
        tableFile = self.open_table(table_name, 'r')
        spaceEntryString, entry_string = self.scan_strings_entry(entry)
        entry_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)

        self.upgrade_db(tableFile, table_name, spaceEntryString)

        entry_id = self.increment_id(tableFile)
        strings_pointer = self.insert_strings(tableFile, entry_string, spaceEntryString)
        entry_pointer, last_entry_pointer, next_entry_pointer = self.get_new_entry_pointer(tableFile, entry_signature)

        tableFile.write_integer_to(entry_id, self.size_of_int(1), entry_pointer)
        tableFile.write_fields(self, table_name, strings_pointer, entry)
        tableFile.write_integer(last_entry_pointer, self.size_of_int(1))
        tableFile.write_integer(next_entry_pointer, self.size_of_int(1))

    def get_table_size(self, table_name: str) -> int:
        tableFile = self.open_table(table_name, 'r')
        return self.get(tableFile, 'nb_entry')
    

    def get_complete_table(self, table_name: str) -> list[Entry]:
        tableFile = self.open_table(table_name, 'r')
        
        complete_table = []
        entrySignature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        entry_pointer = self.get(tableFile, 'first_entry')

        while entry_pointer > 0:
            entry, entry_pointer = tableFile.analyse_entry(entrySignature, entry_pointer)
            complete_table.append(entry)
        
        return complete_table
    
    

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

print(db.get_complete_table("cours"))