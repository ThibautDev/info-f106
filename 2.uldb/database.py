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
            deleted_entry_pointer = table_file.read_integer_from(4, deleted_entry_pointer + next_entry_pointer_offset)

    def upgrade_db(self, table_file, table_name, space):
        shift = self.get_string_buffer_shift(table_file, space)
        self.upgrade_string_buffer(table_file, shift)
        self.upgrade_entry_buffer(table_file, table_name, shift)

        return shift

    def insert_strings(self, table_file: BinaryFile, entry_string: list[str], string_space) -> list[int]:
        free_string_space_pointer = self.get(table_file, 'free_string_space')
        strings_pointer = []

        table_file.goto(free_string_space_pointer)
        for string in entry_string:
            strings_pointer.append(table_file.current_pos)
            table_file.write_string(string)

        free_string_space_pointer_pointer = self.get_pointer(table_file, 'free_string_space')
        table_file.increment_int_from(string_space, 4, free_string_space_pointer_pointer)

        if len(strings_pointer) == 1:
            return strings_pointer[0]
        else:
            return strings_pointer
    
    def get_new_entry_pointer(self, table_file: BinaryFile, field_signature):
        last_entry_pointer, first_deleted_entry_pointer = self.get(table_file, ['last_entry', 'first_deleted_entry'])
        last_entry_pointer_offset =self.size_of_int(len(field_signature))
        next_entry_pointer_offset = last_entry_pointer_offset + self.size_of_int(1)

        if first_deleted_entry_pointer > 0:
            entry_pointer = first_deleted_entry_pointer

            last_entry_pointer_pointer = self.get_pointer(table_file, 'last_entry')
            last_entry_next_entry_pointer_pointer = last_entry_pointer + next_entry_pointer_offset
            
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_pointer_pointer)
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_next_entry_pointer_pointer)

            # Unlist to the delete entry
            last_deleted_entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + last_entry_pointer_offset)
            next_deleted_entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

            print(last_deleted_entry_pointer, next_deleted_entry_pointer)

            if last_deleted_entry_pointer > 0:
                last_deleted_next_entry_pointer = last_deleted_entry_pointer + next_entry_pointer_offset
                table_file.write_integer_to(next_deleted_entry_pointer, self.size_of_int(1), last_deleted_next_entry_pointer)
            else:
                first_deleted_entry_pointer = self.get_pointer(table_file, 'first_deleted_entry')
                table_file.write_integer_to(next_deleted_entry_pointer, self.size_of_int(1), first_deleted_entry_pointer)

            if next_deleted_entry_pointer > 0:
                next_deleted_last_entry_pointer = next_deleted_entry_pointer + last_entry_pointer_offset
                table_file.write_integer_to(last_deleted_entry_pointer, self.size_of_int(1), next_deleted_last_entry_pointer)
                

        elif last_entry_pointer > 0:
            entry_pointer = table_file.get_size()

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
    
    def get_field_info(self, field_signature, field_name, shallBeList = False):
        field_offset = []

        for field_index, field in enumerate(field_signature):
            if field[0] in field_name:
                field_offset.append((self.size_of_int(field_index), field[1]))

        if len(field_offset) == 1 and not shallBeList:
            return field_offset[0]
        else:
            return field_offset
            
    def read_field(self, table_file: BinaryFile, entry_pointer, field_infos):
        field_offset, field_type = field_infos
        
        if field_type == FieldType.INTEGER:
            field = table_file.read_integer_from(self.size_of_int(1), entry_pointer + field_offset)
        else:
            string_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + field_offset)
            field = table_file.read_string_from(string_pointer)

        return field
            
    def for_entry(self, table_name, field_name, field_value, action, select_fields = None):
        table_file = self.open_table(table_name, 'r')
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        
        field_info = self.get_field_info(field_signature, field_name)
        next_entry_pointer_offset = self.size_of_int(len(field_signature) + 1)

        if select_fields != None:
            field_signature = self.get_field_info(field_signature, select_fields, shallBeList = True)

        entry_pointer = self.get(table_file, 'first_entry')

        while entry_pointer > 0:
            field = self.read_field(table_file, entry_pointer, field_info)

            if field == field_value:
                return action(table_file, field_signature, entry_pointer)
            
            entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

        return None
    
    def for_entries(self, table_name, field_name, field_value, action, select_fields = None):
        action_list = []
        action_status = False

        table_file = self.open_table(table_name, 'r')
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        
        field_info = self.get_field_info(field_signature, field_name)
        next_entry_pointer_offset = self.size_of_int(len(field_signature) + 1)

        if select_fields != None:
            field_signature = self.get_field_info(field_signature, select_fields, shallBeList = True)

        entry_pointer = self.get(table_file, 'first_entry')

        while entry_pointer > 0:
            field = self.read_field(table_file, entry_pointer, field_info)

            if field == field_value:
                print("ok")
                action_list.append(action(table_file, field_signature, entry_pointer))
                action_status = True

            entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

        return action_list, action_status
    
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


    def get_entry(self, table_name: str, field_name: str, field_value: Field) -> Entry | None:
        return self.for_entry(table_name, field_name, field_value, self.read_entry)
    
    def get_entries(self, table_name: str, field_name: str, field_value: Field) -> list[Entry]:
        action_list, _ = self.for_entries(table_name, field_name, field_value, self.read_entry)
        return action_list
    
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

        if len(fields) == 1:
            return fields[0]
        else:
            return tuple(fields)
    
    def select_entry(self, table_name: str, fields: tuple[str], field_name: str, field_value: Field) -> Field | tuple[Field]:
        return self.for_entry(table_name, field_name, field_value, self.read_selection, fields)
    
    def select_entries(self, table: str, fields: tuple[str], field_name: str, field_value: Field) -> list[Field | tuple[Field]]:
        action_list, _ =  self.for_entries(table, field_name, field_value, self.read_selection, fields)
        return action_list
    
    def update_entries(self, table_str: str, cond_name: str, cond_value: Field, update_name: str, update_value: Field) -> bool:
        update_status = False

        table_file = self.open_table(table_str, 'r')
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_str)
        
        field_info = self.get_field_info(field_signature, cond_name)
        field_to_update_info = self.get_field_info(field_signature, update_name)
        
        next_entry_pointer_offset = self.size_of_int(len(field_signature) + 1)

        entry_pointer = self.get(table_file, 'first_entry')

        while entry_pointer > 0:
            field = self.read_field(table_file, entry_pointer, field_info)

            if field == cond_value:
                field_offset, field_type = field_to_update_info
                field_pointer = entry_pointer + field_offset

                if field_type == FieldType.INTEGER:
                    if isinstance(update_value, int):
                        table_file.write_integer_to(update_value, self.size_of_int(1), field_pointer)
                    else:
                        raise ValueError
                else:
                    if isinstance(update_value, str):
                        string_pointer = table_file.read_integer_from(self.size_of_int(1), field_pointer)
                        current_string = table_file.read_string_from(string_pointer)

                        if len(current_string) >= len(update_value):
                            table_file.write_string_to(update_value, string_pointer)
                        else:
                            spaceEntryString = len(update_value) + 2

                            shift = self.upgrade_db(table_file, table_str, len(update_value) + 2)
                            entry_pointer += shift
                            field_pointer += shift

                            strings_pointer = self.insert_strings(table_file, [update_value], spaceEntryString)
                            
                            table_file.write_integer_to(strings_pointer, self.size_of_int(1), field_pointer)
                    else:
                        raise ValueError

                update_status = True

            entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

        return update_status
    
    def unlist_entry(self, table_file: BinaryFile, pointer_offset, entry_pointers):
        last_entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointers["last_entry"])
        next_entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointers["next_entry"])

        if last_entry_pointer > 0:
            last_entry_next_entry_pointer = last_entry_pointer + pointer_offset["next_entry"]
        else:
            last_entry_next_entry_pointer = self.get_pointer(table_file, 'first_entry')

        if next_entry_pointer > 0:
            next_entry_last_entry_pointer = next_entry_pointer + pointer_offset["last_entry"]
        else:
            next_entry_last_entry_pointer = self.get_pointer(table_file, 'last_entry')

        table_file.write_integer_to(next_entry_pointer, self.size_of_int(1), last_entry_next_entry_pointer)
        table_file.write_integer_to(last_entry_pointer, self.size_of_int(1), next_entry_last_entry_pointer)

        nb_entry_pointer = self.get_pointer(table_file, 'nb_entry')
        table_file.increment_int_from(-1, self.size_of_int(1), nb_entry_pointer)

    def list_to_delet_entry(self, table_file: BinaryFile, entry_pointer, pointer_offset, entry_pointers):
        first_deleted_entry_pointer = self.get_pointer(table_file, 'first_deleted_entry')
        next_deleted_entry = table_file.read_integer_from(self.size_of_int(1), first_deleted_entry_pointer)

        table_file.write_integer_to(entry_pointer, self.size_of_int(1), first_deleted_entry_pointer)

        table_file.write_integer_to(-1, self.size_of_int(1), entry_pointers["last_entry"])
        table_file.write_integer_to(next_deleted_entry, self.size_of_int(1), entry_pointers["next_entry"])

        if next_deleted_entry > 0:
            next_deleted_entry_last_entry_pointer = next_deleted_entry + pointer_offset["last_entry"]
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), next_deleted_entry_last_entry_pointer)

    def delete_entry(self, table_file: BinaryFile, field_signature, entry_pointer):
        pointer_offset = {}
        pointer_offset["last_entry"] = self.size_of_int(len(field_signature))
        pointer_offset["next_entry"] = pointer_offset["last_entry"] + self.size_of_int(1)

        entry_pointers = {}
        entry_pointers["last_entry"] = entry_pointer + pointer_offset["last_entry"]
        entry_pointers["next_entry"] = entry_pointer + pointer_offset["next_entry"]
        
        self.unlist_entry(table_file, pointer_offset, entry_pointers)
        self.list_to_delet_entry(table_file, entry_pointer, pointer_offset, entry_pointers)

    def delete_entries(self, table_name: str, field_name: str, field_value: Field) -> bool:
        _, action_status = self.for_entries(table_name, field_name, field_value, self.delete_entry)
        return action_status

COURSES = [
    {'MNEMONIQUE': 101, 'NOM': 'Programmation',
     'COORDINATEUR': 'Thierry Massart', 'CREDITS': 5},
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

# db.update_entry(
#         'cours',
#         'id', 1,
#         'NOM', "testttestttestttestttestttestt"
# )

db.delete_entries('cours', 'CREDITS', 5)

for entry in db.get_complete_table('cours'):
    print(entry)