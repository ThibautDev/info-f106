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
        
    def get_string_header_pointer(self, table_file: BinaryFile):
        nColumn = table_file.read_integer_from(self.size_of_int(1), 4)

        for _ in range(nColumn):
            table_file.read_integer(1)
            table_file.read_string()

        return table_file.current_pos
    
    def get_pointer(self, table_file: BinaryFile, pointers_name: str | list[str]):
        '''
        Powerfull fonction that can give any pointer of the database
        '''
        
        # Get headers pointers
        string_header_pointer = self.get_string_header_pointer(table_file)
        entry_header_pointer = table_file.read_integer_from(self.size_of_int(1), string_header_pointer + 8)

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
        
    def get(self, table_file: BinaryFile, pointers_name: str | list[str]):
        pointers = self.get_pointer(table_file, pointers_name)

        if isinstance(pointers_name, str):
            return table_file.read_integer_from(self.size_of_int(1), pointers)
        else:
            return [table_file.read_integer_from(self.size_of_int(1), pointer) for pointer in pointers]
    
    def get_table_signature(self, table_name: str) -> TableSignature:        
        table_file = self.open_table(table_name, 'r')
        
        tableSignature = []

        nColumn = table_file.read_integer_from(self.size_of_int(1), 4)
        for _ in range(nColumn):
            cellType = FieldType(table_file.read_integer(1))
            cellName = table_file.read_string()
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
    
    def get_string_buffer_shift(self, table_file: BinaryFile, space: int):
        stringBufferPointer, freeSpaceStringBufferPointer, entryBufferPointer = self.get(table_file, ['first_string', 'free_string_space', 'entry_buffer'])

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
     
    def upgrade_string_buffer(self, table_file: BinaryFile, shift):
        freeSpaceStringBufferPointerPointer, entry_buffer_pointer  = self.get_pointer(table_file, ['free_string_space', 'entry_buffer'])
        freeSpaceStringBufferPointer = table_file.read_integer_from(self.size_of_int(1), freeSpaceStringBufferPointerPointer)
        table_file.shift_from(freeSpaceStringBufferPointer, shift)
        table_file.increment_int_from(shift, self.size_of_int(1), entry_buffer_pointer)
        
    def upgrade_entry_buffer(self, table_file: BinaryFile, table_name, shift):
        pointersToShift = self.get_pointer(table_file, ['first_entry', 'last_entry', 'first_deleted_entry'])

        for pointer in pointersToShift:
            table_file.increment_int_from(shift, 4, pointer)

        nb_id = self.get(table_file, 'last_id')
        last_entry_pointer_offset =  self.size_of_int(1 + len(self.get_table_signature(table_name)))
        next_entry_pointer_offset = self.size_of_int(2 + len(self.get_table_signature(table_name)))

        entry_pointer, deleted_entry_pointer = self.get(table_file, ['first_entry', 'first_deleted_entry'])

        while entry_pointer > 0:
            table_file.increment_int_from(shift, self.size_of_int(1), entry_pointer + last_entry_pointer_offset)
            table_file.increment_int_from(shift, self.size_of_int(1), entry_pointer + next_entry_pointer_offset)
            entry_pointer = table_file.read_integer_from(4, entry_pointer + next_entry_pointer_offset)

        while deleted_entry_pointer > 0:
            table_file.increment_int_from(shift, self.size_of_int(1), deleted_entry_pointer + last_entry_pointer_offset)
            table_file.increment_int_from(shift, self.size_of_int(1), deleted_entry_pointer + next_entry_pointer_offset)
            entry_pointer = table_file.read_integer_from(4, deleted_entry_pointer + next_entry_pointer_offset)

    def upgrade_db(self, table_file, table_name, space):
        shift = self.get_string_buffer_shift(table_file, space)
        self.upgrade_string_buffer(table_file, shift)
        self.upgrade_entry_buffer(table_file, table_name, shift)

    def insert_strings(self, table_file: BinaryFile, entry_string: list[str], string_space) -> list[int]:
        free_string_space_pointer = self.get(table_file, 'free_string_space')
        strings_pointer = []

        table_file.goto(free_string_space_pointer)
        for string in entry_string:
            strings_pointer.append(table_file.current_pos)
            table_file.write_string(string)

        free_string_space_pointer_pointer = self.get_pointer(table_file, 'free_string_space')
        table_file.increment_int_from(string_space, 4, free_string_space_pointer_pointer)

        return strings_pointer
    
    def get_new_entry_pointer(self, table_file: BinaryFile, table_signature):
        last_entry_pointer, first_deleted_entry_pointer = self.get(table_file, ['last_entry', 'first_deleted_entry'])

        if first_deleted_entry_pointer > 0:
            entry_pointer = first_deleted_entry_pointer

            # TODO

        elif last_entry_pointer > 0:
            entry_pointer = table_file.get_size()

            next_entry_pointer_offset = self.size_of_int(len(table_signature) + 1)

            last_entry_pointer_pointer = self.get_pointer(table_file, 'last_entry')
            last_entry_next_entry_pointer_pointer = last_entry_pointer + next_entry_pointer_offset

            table_file.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_pointer_pointer)
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_next_entry_pointer_pointer)
        else:
            first_entry_pointer_pointer, last_entry_pointer_pointer = self.get_pointer(table_file, ['first_entry', 'last_entry'])
            entry_pointer = table_file.get_size()
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), first_entry_pointer_pointer)
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_pointer_pointer)

        return entry_pointer, last_entry_pointer, -1
    
    def increment_id(self, table_file: BinaryFile):
        last_id_pointer, nb_entry_pointer = self.get_pointer(table_file, ['last_id', 'nb_entry'])

        table_file.increment_int_from(1, self.size_of_int(1), last_id_pointer)
        table_file.increment_int_from(1, self.size_of_int(1), nb_entry_pointer)

        new_id = self.get(table_file, 'last_id')
        return new_id
    
    def add_entry(self, table_name: str, entry: Entry) -> None:
        table_file = self.open_table(table_name, 'r')
        spaceEntryString, entry_string = self.scan_strings_entry(entry)
        entry_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)

        self.upgrade_db(table_file, table_name, spaceEntryString)

        entry_id = self.increment_id(table_file)
        strings_pointer = self.insert_strings(table_file, entry_string, spaceEntryString)
        entry_pointer, last_entry_pointer, next_entry_pointer = self.get_new_entry_pointer(table_file, entry_signature)

        table_file.write_integer_to(entry_id, self.size_of_int(1), entry_pointer)
        table_file.write_fields(self, table_name, strings_pointer, entry)
        table_file.write_integer(last_entry_pointer, self.size_of_int(1))
        table_file.write_integer(next_entry_pointer, self.size_of_int(1))

    def get_table_size(self, table_name: str) -> int:
        table_file = self.open_table(table_name, 'r')
        return self.get(table_file, 'nb_entry')
    

    def get_complete_table(self, table_name: str) -> list[Entry]:
        table_file = self.open_table(table_name, 'r')
        
        complete_table = []
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        entry_pointer = self.get(table_file, 'first_entry')

        while entry_pointer > 0:
            entry, entry_pointer = table_file.analyse_entry(field_signature, entry_pointer)
            complete_table.append(entry)
        
        return complete_table
    
    def get_field_info(self, field_signature, field_name):
        field_offset = []

        for field_index, field in enumerate(field_signature):
            if field[0] in field_name:
                field_offset.append((self.size_of_int(field_index), field[1]))

        if len(field_offset) == 1:
            return field_offset[0]
        else:
            return field_offset
        
    def read_entry(self, table_file: BinaryFile, field_signature, entry_pointer):
        entry = {}
        table_file.goto(entry_pointer)

        for field in field_signature:
            fieldName = field[0]
            fieldType = repr(field[1])

            if fieldType == repr(FieldType.INTEGER):
                entry[fieldName] = table_file.read_integer(4)
            else:
                string_pointer = table_file.read_integer(4)
                current_field_pointer = table_file.current_pos
                entry[fieldName] = table_file.read_string_from(string_pointer)
                table_file.goto(current_field_pointer)

        return entry
    
    def read_field(self, table_file: BinaryFile, entry_pointer, field_infos):
        field_offset, field_type = field_infos
        
        if field_type == FieldType.INTEGER:
            field = table_file.read_integer_from(self.size_of_int(1), entry_pointer + field_offset)
        else:
            string_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + field_offset)
            field = table_file.read_string_from(string_pointer)

        return field
    
    def read_selection(self, table_file: BinaryFile, selection, entry_pointer):
        fields = []

        for field in selection:
            field_offset = field[0]
            field_type = field[1]
            
            if field_type == FieldType.INTEGER: 
                fields.append(table_file.read_integer_from(self.size_of_int(1), entry_pointer + field_offset))
            else:
                string_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + field_offset)
                fields.append(table_file.read_string_from(string_pointer))

        return tuple(fields)

    def get_entry(self, table_name: str, field_name: str, field_value: Field) -> Entry | None:
        table_file = self.open_table(table_name, 'r')
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        
        field_info = self.get_field_info(field_signature, field_name)
        next_entry_pointer_offset = self.size_of_int(len(field_signature) + 1)

        entry_pointer = self.get(table_file, 'first_entry')

        while entry_pointer > 0:
            field = self.read_field(table_file, entry_pointer, field_info)

            if field == field_value:
                return self.read_entry(table_file, field_signature, entry_pointer)
            
            entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

        return None
    
    def get_entries(self, table_name: str, field_name: str, field_value: Field) -> list[Entry]:
        entries = []

        table_file = self.open_table(table_name, 'r')
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        
        field_info = self.get_field_info(field_signature, field_name)
        next_entry_pointer_offset = self.size_of_int(len(field_signature) + 1)

        entry_pointer = self.get(table_file, 'first_entry')

        while entry_pointer > 0:
            field = self.read_field(table_file, entry_pointer, field_info)

            if field == field_value:
                entries.append(self.read_entry(table_file, field_signature, entry_pointer))
            
            entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

        return entries
    
    def select_entry(self, table_name: str, fields: tuple[str], field_name: str, field_value: Field) -> Field | tuple[Field]:
        table_file = self.open_table(table_name, 'r')
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)

        field_info = self.get_field_info(field_signature, field_name)
        selection = self.get_field_info(field_signature, fields)
        next_entry_pointer_offset = self.size_of_int(len(field_signature) + 1)

        entry_pointer = self.get(table_file, 'first_entry')

        while entry_pointer > 0:
            field = self.read_field(table_file, entry_pointer, field_info)

            if field == field_value:
                return self.read_selection(table_file, selection, entry_pointer)
            
            entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

        return None
    
    def select_entries(self, table: str, fields: tuple[str], field_name: str, field_value: Field) -> list[Field | tuple[Field]]:
        entry_fields = set()

        table_file = self.open_table(table, 'r')
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table)

        field_info = self.get_field_info(field_signature, field_name)
        selection = self.get_field_info(field_signature, fields)
        next_entry_pointer_offset = self.size_of_int(len(field_signature) + 1)

        entry_pointer = self.get(table_file, 'first_entry')

        while entry_pointer > 0:
            field = self.read_field(table_file, entry_pointer, field_info)

            if field == field_value:
                entry_fields.add(self.read_selection(table_file, selection, entry_pointer))
            
            entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

        return entry_fields
        
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

print(db.get_entry('cours', 'NOM', 'Programmation'))
# print(db.select_entries('cours', ('MNEMONIQUE', 'NOM'), 'CREDITS', 5))