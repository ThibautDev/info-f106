from sys import argv
from database import Database
from enum import Enum

class FieldType(Enum):
    INTEGER = 1
    STRING = 2

class run_time:
    def __init__(self):
        self.db = None
        self.start()

    def exec_request(self, request: str):
        '''
        Execute a given request
        '''

        # Link all function name string to all function
        functions = {
            "open": self.open,
            "create_table": self.create_table,
            "delete_table": self.delete_table,
            "list_tables": self.list_tables,
            "insert_to": self.insert_to,
            "from_if_get": self.from_if_get,
            "from_delete_where": self.from_delete_where,
            "from_update_where": self.from_update_where
        }

        # Split the function to get the function name and the arguments
        function_name = request.split('(')[0]
        argument = request.split('(')[1].split(')')[0].split(',')

        # Execute the function depending if there are arguments or not
        try:
            if len(argument) == 1 and argument[0] == '':
                functions[function_name]()
            else:
                functions[function_name](*argument)
        except:
            raise ValueError

    def parse_field(self, field: str):
        '''
        Parse field format
        
        Example : " CRED=2 " -> str('CRED'), int(2)
        '''
        field_name, field_value = field.split('=')

        # Check if field_value is a string or int
        if field_value[0] == '"' and field_value[-1] == '"':
            # This field value is a string
            field_value = field_value[1:-1]
        else:
            # If is not in quotation marks, it's should be an int
            try:
                field_value = int(field_value)
            except:
                print("Wrong field value format")

        # field_name should be always a string, so no need to check
        return field_name, field_value

    def open(self, db_name):
        '''
        Check if no db are open. If this is true, open a db
        '''
        if self.db == None:
            self.db = Database(db_name)
        else:
            print("A table is database is already open")

    def create_table(self, table_name, *fields: list[str]):
        '''
        Parse table info and check if the format is good and create a new table.
        '''
        fields_info = []
        for field in fields:
            field_name, field_type = field.split("=")

            if field_type == "INTEGER":
                field_type = FieldType.INTEGER
            elif field_type == "STRING":
                field_type = FieldType.STRING
            else:
                raise ValueError
            
            fields_info.append((field_name, field_type))

        self.db.create_table(table_name, *fields_info)
            
    def delete_table(self, table_name):
        '''
        Check if the table existe and delete it if it's the case.
        '''
        if table_name in self.db.list_tables():
            self.db.delete_table(table_name)
        else:
            print("This table doesn't exist")

    def list_tables(self):
        '''
        Show a liste of all table of the db
        '''
        list_table = self.db.list_tables()

        # Print one by one all table names
        for table in list_table:
            print(table)

    def insert_to(self, table_name, *fields: list[str]):
        '''
        Parse all field into a dict and execute the insert request
        '''
        entry = {}

        for field in fields:
            field_name, field_value = self.parse_field(field)
            entry[field_name] = field_value

        self.db.add_entry(table_name, entry)

    def from_if_get(self, table_name, cond: str, *field):
        '''
        Get all selected fields that satisfy the condition
        '''

        cond_field_name, cond_field_value = self.parse_field(cond)

        # If * is mentioned, that means it want all field
        if '*' in field:
            table_signature = self.db.get_table_signature(table_name)
            field = [field[0] for field in table_signature]

        query = self.db.select_entries(table_name, field, cond_field_name, cond_field_value)

        # Print all field one by one
        for field in query:
            print(field)

    def from_delete_where(self, table_name, cond):
        '''
        Delete all selected fields that satisfy the condition
        '''
        cond_field_name, cond_field_value = self.parse_field(cond)

        self.db.delete_entries(table_name, cond_field_name, cond_field_value)

    def from_update_where(self, table_name, cond, edit):
        '''
        Update all selected fields with given propreties that satisfy the condition
        '''
        cond_field_name, cond_field_value = self.parse_field(cond)
        edit_field_name, edit_field_value = self.parse_field(edit)

        self.db.update_entries(table_name, cond_field_name, cond_field_value, edit_field_name, edit_field_value)

    def run_script(self, path):
        '''
        Open a file and execute one by one all request
        '''
        with open(path, 'r') as file:
            for request in file:
                self.exec_request(request)

    def interactive(self):
        '''
        Ask to the user all request to enter untild the used enter 'quit' or 'q'
        '''
        command = input('uldb:: ')

        while command not in ['quit', 'q']:
            self.exec_request(command)
            command = input('uldb:: ')

    def start(self):
        '''
        Check if how the user want to use uldb
        '''

        if len(argv) == 2 and argv[1].split('.')[1] == 'uldb':
            # Give argument are valide file so run it in script mode
            self.run_script(argv[1])

        elif len(argv) == 1:
            # We run in interactive mode
            self.interactive()
        else:
            # We don't run the file
            raise ValueError

if __name__ == '__main__':
    run_time()