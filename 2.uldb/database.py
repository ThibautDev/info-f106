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
        makedirs(name, exist_ok=True) # Create database directory and do not raise an error if the directory already exists

    def size_of_int(self, nb_int):
        return nb_int * 4

    def list_tables(self) -> list[str]:
        '''
        List all file names in the database directory without the extensions.
        '''

        return [file_name.split('.')[0] for file_name in listdir(self.name)]

    def open_table(self, table_name, method):
        '''
        Open the table file if it exists, or create a new one if requested.
        '''

        if table_name in self.list_tables() or method == 'x':
            try:
                file_name = self.name + '/' + table_name + '.table'
                return BinaryFile(open(file_name, method + '+b'))  # Open file with chosen method
            except:
                raise ValueError
        else:
            raise ValueError
            
    def create_table(self, table_name: str, *fields: TableSignature) -> None:
        '''
        Create an empty table file with default headers and pointers.
        '''

        pointer_size = self.size_of_int(1) # For readability
        table_file = self.open_table(table_name, 'x')
        
        table_file.write_integer(int(0x42444C55), self.size_of_int(1))  # Write magic constant (ULDB in ASCII)
        table_file.write_integer(len(fields), self.size_of_int(1)) # Write number of fields

        for field in fields: # Initialize each column
            table_file.write_integer(field[1].value, 1) # Field type
            table_file.write_string(field[0]) # Field name

        file_size = table_file.get_size()
        size_string_buffer = 16

        table_file.write_integer(file_size + pointer_size * 3, pointer_size) # Initialize string buffer pointer
        table_file.write_integer(file_size + pointer_size * 3, pointer_size) # Initialize next usable space pointer
        table_file.write_integer(file_size + pointer_size * 3 + size_string_buffer, pointer_size) # Initialize pointer to entry buffer header

        table_file.write_integer(0, size_string_buffer) # Allocate space for the string buffer

        table_file.write_integer(0, pointer_size) # Initialize last used ID (0 as default)
        table_file.write_integer(0, pointer_size) # Initialize number of entries (0 as default)
        table_file.write_integer(-1, pointer_size) # Initialize pointer to the first entry (-1 as default)
        table_file.write_integer(-1, pointer_size) # Initialize pointer to the first entry (-1 as default)
        table_file.write_integer(-1, pointer_size) # Initialize pointer to the first 

    def delete_table(self, table_name: str) -> None:
        '''
        Delete the table file if it exists.
        '''

        try: # Try to delete the file
            remove(self.name + '/' + table_name + '.table')
        except: # If it doesn't work, that means it doesn't exist
            raise ValueError
        
    def get_string_header_pointer(self, table_file: BinaryFile):
        '''
        Get the header pointer of the string buffer to retrieve pointers.
        '''
        n_field = table_file.read_integer_from(self.size_of_int(1), 4)

        for _ in range(n_field):
            table_file.read_integer(1)
            table_file.read_string()

        return table_file.current_pos
    
    def get_pointer(self, table_file: BinaryFile, pointers_name: str | list[str]):
        '''
        Powerful function that can retrieve any pointer in the database.
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

        # Return a int or a string depend of the entry
        if isinstance(pointers_name, str):
            return pointers[pointers_name]
        else:
            return [pointers[name] for name in pointers_name]
        
    def get(self, table_file: BinaryFile, pointers_name: str | list[str]):
        '''
        Get the value directly from the pointer.
        '''
        pointers = self.get_pointer(table_file, pointers_name)

        # Return a int or a string depend of the entry
        if isinstance(pointers_name, str):
            return table_file.read_integer_from(self.size_of_int(1), pointers)
        else:
            return [table_file.read_integer_from(self.size_of_int(1), pointer) for pointer in pointers]
    
    def get_table_signature(self, table_name: str) -> TableSignature:
        '''
        Get a list of all fields composing an entry.
        '''
        table_file = self.open_table(table_name, 'r')
        
        table_signature = []

        n_field = table_file.read_integer_from(self.size_of_int(1), 4)

        for _ in range(n_field): # Browse all field and add propreties to the list
            cell_type = FieldType(table_file.read_integer(1))
            cell_name = table_file.read_string()
            table_signature.append((cell_name, cell_type))

        return table_signature
    
    def scan_strings_entry(self, entry: Entry) -> int:
        '''
        Return the space this entry will take in the string buffer and a list of all strings to add.
        '''
        string_space = 0
        strings = []

        for info in entry:
            if isinstance(entry[info], str):
                string_space += len(entry[info].encode("utf-8")) + 2 # Get the size this string will take in the file
                strings.append(entry[info])

        return string_space, strings
    
    def get_string_buffer_shift(self, table_file: BinaryFile, space: int):
        '''
        If the new entry didn't fit in the string buffer, 
        calculate the shift to make it fit and keep the string buffer size a power of 2.
        '''
        string_buffer_pointer, free_space_string_buffer_pointer, entry_buffer_pointer = self.get(table_file, ['first_string', 'free_string_space', 'entry_buffer'])

        # Calculate spaces
        string_buffer_space = entry_buffer_pointer - string_buffer_pointer
        string_buffer_used_space = free_space_string_buffer_pointer - string_buffer_pointer

        # Approximate the new string buffer space to the next power of 2
        new_string_buffer_space = string_buffer_space

        while new_string_buffer_space < string_buffer_used_space + space:
            new_string_buffer_space *= 2

        # Calculate the shift 
        shift = new_string_buffer_space - string_buffer_space
        return shift
     
    def upgrade_string_buffer(self, table_file: BinaryFile, shift):
        '''
        Upgrade the string buffer and apply the shift to all pointers
        '''
        free_space_string_buffer_pointerPointer, entry_buffer_pointer  = self.get_pointer(table_file, ['free_string_space', 'entry_buffer'])
        free_space_string_buffer_pointer = table_file.read_integer_from(self.size_of_int(1), free_space_string_buffer_pointerPointer)
        table_file.shift_from(free_space_string_buffer_pointer, shift)
        table_file.increment_int_from(shift, self.size_of_int(1), entry_buffer_pointer)
        
    def upgrade_entry_buffer(self, table_file: BinaryFile, table_name, shift):
        '''
        Upgrade the entry buffer and apply shift to all pointer
        '''
        pointers_to_shift = self.get_pointer(table_file, ['first_entry', 'last_entry', 'first_deleted_entry'])

        # Shift all pointer of the header
        for pointer in pointers_to_shift:
            table_file.increment_int_from(shift, self.size_of_int(1), pointer)

        # Get the offset of all entry pointer 
        last_entry_pointer_offset =  self.size_of_int(1 + len(self.get_table_signature(table_name)))
        next_entry_pointer_offset = self.size_of_int(2 + len(self.get_table_signature(table_name)))

        # Apply the shift to all entry pointer of each list
        entry_pointer, deleted_entry_pointer = self.get(table_file, ['first_entry', 'first_deleted_entry'])

        while entry_pointer > 0:
            table_file.increment_int_from(shift, self.size_of_int(1), entry_pointer + last_entry_pointer_offset)
            table_file.increment_int_from(shift, self.size_of_int(1), entry_pointer + next_entry_pointer_offset)
            entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

        while deleted_entry_pointer > 0:
            table_file.increment_int_from(shift, self.size_of_int(1), deleted_entry_pointer + last_entry_pointer_offset)
            table_file.increment_int_from(shift, self.size_of_int(1), deleted_entry_pointer + next_entry_pointer_offset)
            deleted_entry_pointer = table_file.read_integer_from(self.size_of_int(1), deleted_entry_pointer + next_entry_pointer_offset)

    def upgrade_db(self, table_file, table_name, space):
        '''
        Get the shift and apply it if needed 
        '''
        shift = self.get_string_buffer_shift(table_file, space)
        if shift > 0:
            self.upgrade_string_buffer(table_file, shift)
            self.upgrade_entry_buffer(table_file, table_name, shift)

        return shift

    def insert_strings(self, table_file: BinaryFile, entry_string: list[str], string_space) -> list[int]:
        '''
        Insert strings into the string buffer and return a list of pointers to all strings.
        '''
        free_string_space_pointer = self.get(table_file, 'free_string_space')
        strings_pointer = []

        table_file.goto(free_string_space_pointer)
        for string in entry_string:
            strings_pointer.append(table_file.current_pos)
            table_file.write_string(string)

        free_string_space_pointer_pointer = self.get_pointer(table_file, 'free_string_space')
        table_file.increment_int_from(string_space, self.size_of_int(1), free_string_space_pointer_pointer)

        if len(strings_pointer) == 1:
            return strings_pointer[0]
        else:
            return strings_pointer
    
    def set_new_entry_pointer(self, table_file: BinaryFile, field_signature):
        '''
        Get all entry pointers and set the entry buffer to add a new entry.
        '''
        last_entry_pointer, first_deleted_entry_pointer = self.get(table_file, ['last_entry', 'first_deleted_entry'])
        last_entry_pointer_offset =self.size_of_int(len(field_signature))
        next_entry_pointer_offset = last_entry_pointer_offset + self.size_of_int(1)

        if first_deleted_entry_pointer > 0:
            # Use a deleted place
            entry_pointer = first_deleted_entry_pointer

            last_entry_pointer_pointer = self.get_pointer(table_file, 'last_entry')
            last_entry_next_entry_pointer_pointer = last_entry_pointer + next_entry_pointer_offset
            
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_pointer_pointer)
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_next_entry_pointer_pointer)

            # Unlist to the delete entry
            last_deleted_entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + last_entry_pointer_offset)
            next_deleted_entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

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
            # Add to the end of the file
            entry_pointer = table_file.get_size()

            last_entry_pointer_pointer = self.get_pointer(table_file, 'last_entry')
            last_entry_next_entry_pointer_pointer = last_entry_pointer + next_entry_pointer_offset

            table_file.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_pointer_pointer)
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_next_entry_pointer_pointer)
        else:
            # Set the entry buffer header and add a entry at the end of the file
            first_entry_pointer_pointer, last_entry_pointer_pointer = self.get_pointer(table_file, ['first_entry', 'last_entry'])
            entry_pointer = table_file.get_size()
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), first_entry_pointer_pointer)
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), last_entry_pointer_pointer)

        return entry_pointer, last_entry_pointer, -1
    
    def increment_id(self, table_file: BinaryFile, entry: Entry):
        '''
        Increment nb_entry and set the last used id if provided
        '''

        last_id_pointer, nb_entry_pointer = self.get_pointer(table_file, ['last_id', 'nb_entry'])

        if 'id' in entry.keys():
            table_file.write_integer_to(entry['id'], self.size_of_int(1), last_id_pointer)
        else:
            table_file.increment_int_from(1, self.size_of_int(1), last_id_pointer)

        table_file.increment_int_from(1, self.size_of_int(1), nb_entry_pointer)

        new_id = self.get(table_file, 'last_id')
        return new_id
    
    def write_entry(self, table_file:BinaryFile, table_name, strings_pointer, entry):
        '''
        Write an entry to the entry buffer
        '''
        for field in self.get_table_signature(table_name):
            fieldName = field[0]
            fieldType = field[1]

            # Depend of the field type
            if fieldType == FieldType.INTEGER:
                # Only write the int
                table_file.write_integer(entry[fieldName], 4)
            else:
                # Write the pointer to the string on the string buffer
                stringPointer = strings_pointer.pop(0)
                table_file.write_integer(stringPointer, 4)
    
    def add_entry(self, table_name: str, entry: Entry) -> None:
        '''
        Add the specified entry to the database.
        '''

        table_file = self.open_table(table_name, 'r')
        spaceEntryString, entry_string = self.scan_strings_entry(entry)
        entry_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)

        self.upgrade_db(table_file, table_name, spaceEntryString)

        entry_id = self.increment_id(table_file, entry)

        # Add string to string pointer
        strings_pointer = self.insert_strings(table_file, entry_string, spaceEntryString)
        entry_pointer, last_entry_pointer, next_entry_pointer = self.set_new_entry_pointer(table_file, entry_signature)

        # Add entry to entry pointer
        table_file.write_integer_to(entry_id, self.size_of_int(1), entry_pointer)
        self.write_entry(table_file, table_name, strings_pointer, entry)
        table_file.write_integer(last_entry_pointer, self.size_of_int(1))
        table_file.write_integer(next_entry_pointer, self.size_of_int(1))

    def get_table_size(self, table_name: str) -> int:
        '''
        Get the number of entries in the database.
        '''

        table_file = self.open_table(table_name, 'r')
        return self.get(table_file, 'nb_entry')

    def analyse_entry(self, table_file: BinaryFile, entrySignature, entry_pointer):
        '''
        Read an entry and parse it into a dict
        '''
        entry = {}
        table_file.goto(entry_pointer)

        # Read all field one by one
        for field in entrySignature:
            fieldName = field[0]
            fieldType = field[1]

            # Read field depend of the type
            if fieldType == FieldType.INTEGER: 
                # Only read the int
                entry[fieldName] = table_file.read_integer(4) 
            else: 
                # Only read the string on the string buffer
                stringPointer = table_file.read_integer(4)
                currentPos = table_file.current_pos
                entry[fieldName] = table_file.read_string_from(stringPointer)
                table_file.goto(currentPos)

        # Skip last entry pointer
        table_file.read_integer(self.size_of_int(1))

        # Read next entry pointer
        next_entry_pointer = table_file.read_integer(4)

        return entry, next_entry_pointer

    def get_complete_table(self, table_name: str) -> list[Entry]:
        '''
        Get a list of all entries.
        '''

        table_file = self.open_table(table_name, 'r')
        
        complete_table = []
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        entry_pointer = self.get(table_file, 'first_entry')

            # Browse all entries in the chain until the end
        while entry_pointer > 0:
            entry, entry_pointer = self.analyse_entry(table_file, field_signature, entry_pointer)
            complete_table.append(entry)
        
        return complete_table
    
    def get_field_offset(self, field_signature, field_name, shallBeList = False):
        '''
        Get the offset of the given field to retrieve its value from an entry.
        '''
        field_offset = []

        for field_index, field in enumerate(field_signature):
            if field[0] in field_name:
                field_offset.append((self.size_of_int(field_index), field[1]))

        if len(field_offset) == 1 and not shallBeList:
            return field_offset[0]
        else:
            return field_offset
            
    def read_field(self, table_file: BinaryFile, entry_pointer, field_infos):
        '''
        Read a field from an entry depending on whether it's an integer or a string.
        '''
        field_offset, field_type = field_infos
        
        if field_type == FieldType.INTEGER:
            field = table_file.read_integer_from(self.size_of_int(1), entry_pointer + field_offset)
        else:
            string_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + field_offset)
            field = table_file.read_string_from(string_pointer)

        return field
            
    def for_entry(self, table_name, field_name, field_value, action, select_fields = None):
        '''
        Execute a function on the selected entry and return the result.
        '''
        table_file = self.open_table(table_name, 'r')
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        
        field_info = self.get_field_offset(field_signature, field_name)
        next_entry_pointer_offset = self.size_of_int(len(field_signature) + 1)

        if select_fields != None:
            field_signature = self.get_field_offset(field_signature, select_fields, shallBeList = True)

        entry_pointer = self.get(table_file, 'first_entry')

        # Browse all entry
        while entry_pointer > 0: 
            # If field match exec the function
            field = self.read_field(table_file, entry_pointer, field_info)

            if field == field_value:
                return action(table_file, field_signature, entry_pointer)
            
            entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)

        return None
    
    def for_entries(self, table_name, field_name, field_value, action, select_fields = None):
        '''
        Execute a function on all selected entries and return the results and an action status.
        '''
        action_list = []
        action_status = False

        table_file = self.open_table(table_name, 'r')
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_name)
        
        field_info = self.get_field_offset(field_signature, field_name)
        next_entry_pointer_offset = self.size_of_int(len(field_signature) + 1)

        if select_fields != None:
            field_signature = self.get_field_offset(field_signature, select_fields, shallBeList = True)

        entry_pointer = self.get(table_file, 'first_entry')

        # Browse all entry
        while entry_pointer > 0: 
            # If field match exec the function
            next_entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointer + next_entry_pointer_offset)
            field = self.read_field(table_file, entry_pointer, field_info)

            if type(field) == type(field_value): 
                if field == field_value:
                    action_list.append(action(table_file, field_signature, entry_pointer))
                    action_status = True
            else:
                raise ValueError

            entry_pointer = next_entry_pointer

        return action_list, action_status
    
    def read_entry(self, table_file: BinaryFile, field_signature, entry_pointer):
        '''
        Read all fields of an entry.
        '''
        entry = {}
        table_file.goto(entry_pointer)

        for field in field_signature:
            fieldName = field[0]
            fieldType = repr(field[1])

            if fieldType == repr(FieldType.INTEGER):
                entry[fieldName] = table_file.read_integer(self.size_of_int(1))
            else:
                string_pointer = table_file.read_integer(self.size_of_int(1))
                current_field_pointer = table_file.current_pos
                entry[fieldName] = table_file.read_string_from(string_pointer)
                table_file.goto(current_field_pointer)

        return entry


    def get_entry(self, table_name: str, field_name: str, field_value: Field) -> Entry | None:
        '''
        Get all fields of an entry based on specific properties.
        '''
        return self.for_entry(table_name, field_name, field_value, self.read_entry)
    
    def get_entries(self, table_name: str, field_name: str, field_value: Field) -> list[Entry]:
        '''
        Get all fields of all entries based on specific properties.
        '''
        action_list, _ = self.for_entries(table_name, field_name, field_value, self.read_entry)
        return action_list
    
    def read_selection(self, table_file: BinaryFile, selection, entry_pointer):
        '''
        Read selected fields of an entry.
        '''
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
        '''
        Get specific fields of an entry based on given properties.
        '''
        return self.for_entry(table_name, field_name, field_value, self.read_selection, select_fields = fields)
    
    def select_entries(self, table: str, fields: tuple[str], field_name: str, field_value: Field) -> list[Field | tuple[Field]]:
        '''
        Get specific fields of all entries based on given properties.
        '''
        action_list, _ =  self.for_entries(table, field_name, field_value, self.read_selection, select_fields = fields)
        return action_list
    
    def update_entries(self, table_str: str, cond_name: str, cond_value: Field, update_name: str, update_value: Field) -> bool:
        '''
        Update all entries that meet the given condition with the specified update information.
 
        Note: for readability reasons, for_entries() is rewritten within this function.
        '''
        update_status = False

        table_file = self.open_table(table_str, 'r')
        field_signature = [('id', FieldType.INTEGER)] + self.get_table_signature(table_str)
        
        field_info = self.get_field_offset(field_signature, cond_name)
        field_to_update_info = self.get_field_offset(field_signature, update_name)
        
        next_entry_pointer_offset = self.size_of_int(len(field_signature) + 1)

        entry_pointer = self.get(table_file, 'first_entry')

        # Browse all entry 
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
        '''
        Edit list pointers to remove an entry from the entry list.
        '''

        # Get current entry pointers
        last_entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointers["last_entry"])
        next_entry_pointer = table_file.read_integer_from(self.size_of_int(1), entry_pointers["next_entry"])

        # Check if it's a first or last entry and if we need to edit pointer next to this entry or modify the header
        if last_entry_pointer > 0:
            last_entry_next_entry_pointer = last_entry_pointer + pointer_offset["next_entry"]
        else:
            last_entry_next_entry_pointer = self.get_pointer(table_file, 'first_entry')

        if next_entry_pointer > 0:
            next_entry_last_entry_pointer = next_entry_pointer + pointer_offset["last_entry"]
        else:
            next_entry_last_entry_pointer = self.get_pointer(table_file, 'last_entry')

        # Edit pointer
        table_file.write_integer_to(next_entry_pointer, self.size_of_int(1), last_entry_next_entry_pointer)
        table_file.write_integer_to(last_entry_pointer, self.size_of_int(1), next_entry_last_entry_pointer)

        # Decrement the nb of entry 
        nb_entry_pointer = self.get_pointer(table_file, 'nb_entry')
        table_file.increment_int_from(-1, self.size_of_int(1), nb_entry_pointer)

    def list_to_delet_entry(self, table_file: BinaryFile, entry_pointer, pointer_offset, entry_pointers):
        '''
        Edit list pointers to remove and add the entry to the deleted entry list.
        '''
        first_deleted_entry_pointer = self.get_pointer(table_file, 'first_deleted_entry')
        next_deleted_entry = table_file.read_integer_from(self.size_of_int(1), first_deleted_entry_pointer)

        table_file.write_integer_to(entry_pointer, self.size_of_int(1), first_deleted_entry_pointer)

        table_file.write_integer_to(-1, self.size_of_int(1), entry_pointers["last_entry"])
        table_file.write_integer_to(next_deleted_entry, self.size_of_int(1), entry_pointers["next_entry"])

        if next_deleted_entry > 0:
            next_deleted_entry_last_entry_pointer = next_deleted_entry + pointer_offset["last_entry"]
            table_file.write_integer_to(entry_pointer, self.size_of_int(1), next_deleted_entry_last_entry_pointer)

    def erase_deleted_entry(self, table_name):
        '''
        Reinsert all entries into a new table to delete all previously deleted entries.
        '''
        table_signature = self.get_table_signature(table_name)
        all_entry = [entry for entry in self.get_complete_table(table_name)]

        self.delete_table(table_name)
        self.create_table(table_name, *table_signature)
        for entry in all_entry:
            self.add_entry(table_name, entry)

    def delete_entry(self, table_file: BinaryFile, field_signature, entry_pointer):
        '''
        Calculate pointer offsets and entry pointers, then remove the entry from the entry list and add it to the deleted entry list.
        '''
        pointer_offset = {}
        pointer_offset["last_entry"] = self.size_of_int(len(field_signature))
        pointer_offset["next_entry"] = pointer_offset["last_entry"] + self.size_of_int(1)

        entry_pointers = {}
        entry_pointers["last_entry"] = entry_pointer + pointer_offset["last_entry"]
        entry_pointers["next_entry"] = entry_pointer + pointer_offset["next_entry"]
        
        self.unlist_entry(table_file, pointer_offset, entry_pointers)
        self.list_to_delet_entry(table_file, entry_pointer, pointer_offset, entry_pointers)



    def delete_entries(self, table_name: str, field_name: str, field_value: Field) -> bool:
        '''
        Delete all entries that meet the condition and refactor the file if needed.
        '''
        _, action_status = self.for_entries(table_name, field_name, field_value, self.delete_entry)

        table_file = self.open_table(table_name, 'r')

        start_of_entry_buffer = self.get_pointer(table_file, "first_deleted_entry") + self.size_of_int(1)
        end_of_entry_buffer = table_file.get_size()

        entry_buffer_space = end_of_entry_buffer - start_of_entry_buffer
        entry_size = self.size_of_int(len(self.get_table_signature(table_name)) + 3)

        nb_entry_rel = self.get(table_file, 'nb_entry')

        # Avoid divising by 0 to calcule the ratio entry / deleted entry
        if entry_size != 0:
            nb_entry = entry_buffer_space // entry_size
        else:
            nb_entry = 0

        if nb_entry_rel != 0:
            if nb_entry // nb_entry_rel >= 2:
                self.erase_deleted_entry(table_name)

        return action_status