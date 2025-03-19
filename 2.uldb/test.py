from contextlib import contextmanager
from pathlib import Path
import pytest
COURS_PATH = Path('programme') / 'cours.table'

def get_db(db_name: str) -> 'Database':
    from database import Database
    return Database(db_name)

def get_empty_db(db_name: str) -> 'Database':
    db = get_db(db_name)
    for table_name in db.list_tables():
        db.delete_table(table_name)
    return db

def get_programme_db() -> 'Database':
    from database import FieldType
    db = get_empty_db('programme')
    db.create_table(
        'cours',
        ('MNEMONIQUE', FieldType.INTEGER),
        ('NOM', FieldType.STRING),
        ('COORDINATEUR', FieldType.STRING),
        ('CREDITS', FieldType.INTEGER)
    )
    return db

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

def fill_courses(db: 'Database') -> None:
    for course in COURSES:
        db.add_entry('cours', course)
    return db

def _read_table_file(path: Path) -> bytes:
    import os.path
    assert os.path.isfile(path)
    with open(path, 'rb') as f:
        return f.read()

@contextmanager
def tmpfile(path: str | None = None):
    if path is None:
        import tempfile
        yield tempfile.TemporaryFile()
    else:
        yield open(path, 'r+b')

########################################
#               Partie 1               #
########################################

def test_write_integer():
    from binary import BinaryFile
    with tmpfile() as f:
        file = BinaryFile(f)
        file.write_integer(1, 1)
        file.write_integer(2, 2)
        file.write_integer(3, 1)
        file.goto(0)
        assert file.read_integer(4) == 0x03000201
        assert file.read_integer_from(4, 0) == 0x03000201

def test_write_string():
    from binary import BinaryFile
    with tmpfile() as f:
        file = BinaryFile(f)
        file.write_string('aeé')
        assert file.read_integer_from(2, 0) == 4
        assert file.read_integer_from(1, 2) == ord('a')
        assert file.read_integer_from(1, 3) == ord('e')
        assert file.read_integer_from(2, 4) == -22077
        assert file.read_string_from(0) == 'aeé'

def test_get_size():
    from binary import BinaryFile
    with tmpfile() as f:
        file = BinaryFile(f)
        assert file.get_size() == 0
        file.write_string('eée')
        assert file.get_size() == 6

########################################
#               Partie 2               #
########################################

def test_create_db():
    get_empty_db('programme')

def test_field_types():
    from database import FieldType
    types = set(map(lambda x: getattr(x, 'name'), FieldType))
    assert types == {'STRING', 'INTEGER'}
    assert set(FieldType) == set(map(FieldType, range(1, 3)))

def test_list_table():
    db = get_programme_db()
    del db
    db = get_db('programme')
    assert db.list_tables() == ['cours']

def test_create_table():
    db = get_programme_db()
    del db
    data = _read_table_file(COURS_PATH)
    assert data[:4] == b'ULDB'  # magic constant
    assert data[4:8] == b'\x04\x00\x00\x00'  # number of fields
    signature = b'\x01\x0a\x00MNEMONIQUE' + \
                b'\x02\x03\x00NOM' + \
                b'\x02\x0c\x00COORDINATEUR' + \
                b'\x01\x07\x00CREDITS'
    assert data[8:52] == signature
    assert data[52:56] == b'\x40\x00\x00\x00'  # string buffer pos
    assert data[56:60] == b'\x40\x00\x00\x00'  # available string pos
    assert data[60:64] == b'\x50\x00\x00\x00'  # entry buffer pos
    assert data[64:80] == bytearray(16)  # empty string buffer
    assert data[80:84] == bytearray(4)  # current id
    assert data[84:88] == bytearray(4)  # current size
    assert data[88:96] == b'\xff' * 8  # first and last

def test_create_table_already_exists():
    db = get_programme_db()
    from database import FieldType
    with pytest.raises(ValueError):
        db.create_table('cours', [('MNEMONIQUE', FieldType.INTEGER)])

def test_delete_non_existing_table():
    db = get_empty_db('programme')
    with pytest.raises(ValueError):
        db.delete_table('table')

def test_get_signature_non_existing_table():
    db = get_empty_db('programme')
    with pytest.raises(ValueError):
        db.get_table_signature('COURS')

def test_delete_table():
    db = get_programme_db()
    assert db.list_tables() == ['cours']
    db.delete_table('cours')
    assert db.list_tables() == []

########################################
#               Partie 3               #
########################################

def test_insert_in_table():
    db = get_programme_db()
    entry = {
        'MNEMONIQUE': 101, 'NOM': 'Programmation',
        'COORDINATEUR': 'Thierry Massart', 'CREDITS': 10
    }
    db.add_entry('cours', entry)
    data = _read_table_file(COURS_PATH)
    assert data[52:56] == b'\x40\x00\x00\x00'  # string buffer pos
    assert data[56:60] == b'\x60\x00\x00\x00'  # available string pos
    assert data[60:64] == b'\x60\x00\x00\x00'  # entry buffer pos
    assert data[64:96] == b'\x0d\x00Programmation' + \
                          b'\x0f\x00Thierry Massart'
    assert data[96:100] == b'\x01\x00\x00\x00'  # current id
    assert data[100:104] == b'\x01\x00\x00\x00'  # current size
    assert data[104:108] == b'\x74\x00\x00\x00'  # first
    assert data[108:112] == b'\x74\x00\x00\x00'  # last
    assert data[112:116] == b'\xff\xff\xff\xff'  # first deleted
    assert data[116:120] == b'\x01\x00\x00\x00'  # ID
    assert data[120:124] == b'\x65\x00\x00\x00'  # 101
    assert data[124:128] == b'\x40\x00\x00\x00'  # Programmation
    assert data[128:132] == b'\x4f\x00\x00\x00'  # T. Massart
    assert data[132:136] == b'\x0a\x00\x00\x00'  # 10

def test_get_table_signature():
    from database import FieldType
    db = get_programme_db()
    signature = [
        ('MNEMONIQUE', FieldType.INTEGER),
        ('NOM', FieldType.STRING),
        ('COORDINATEUR', FieldType.STRING),
        ('CREDITS', FieldType.INTEGER)
    ]
    assert db.get_table_signature('cours') == signature

def test_size_on_creation():
    db = get_programme_db()
    assert db.get_table_size('cours') == 0

def test_in_non_existing_table():
    db = get_programme_db() #TODO: question, est-ce normal que ce soit la fonction get_programme_db au lieu de get_empty_db car cours est défini dans la première fonction
    with pytest.raises(ValueError):
        db.add_entry('COURS', COURSES[0])

def test_get_complete_table():
    db = get_programme_db()
    fill_courses(db)
    courses = [course.copy() for course in COURSES]
    for i in range(len(courses)):
        courses[i]['id'] = i+1
    expected = set(map(
        lambda d: frozenset(zip(d.items())),
        courses
    ))
    table = set(map(
        lambda d: frozenset(zip(d.items())),
        db.get_complete_table('cours')
    ))
    assert table == expected

def test_size_after_insert():
    db = get_programme_db()
    fill_courses(db)
    assert db.get_table_size('cours') == len(COURSES)
    assert db.get_table_size('cours') == len(db.get_complete_table('cours'))

def test_get():
    db = get_programme_db()
    fill_courses(db)
    entry = db.get_entry('cours', 'MNEMONIQUE', 101)
    assert entry == COURSES[0] | {'id': 1}
    entries = db.get_entries('cours', 'MNEMONIQUE', 101)
    assert entries == [COURSES[0] | {'id': 1}]
    entries = db.get_entries('cours', 'CREDITS', 10)
    assert {entry['MNEMONIQUE'] for entry in entries} == {101, 103}

# def test_select():
#     db = get_programme_db()
#     fill_courses(db)
#     query = db.select_entry('cours', ('MNEMONIQUE', 'NOM'), 'CREDITS', 5)
#     possibles = {
#         (102, 'Fonctionnement des ordinateurs'),
#         (105, 'Langages de programmation I'),
#         (106, 'Projet d\'informatique I')
#     }
#     assert query in possibles
#     query = db.select_entries('cours', ('MNEMONIQUE', 'NOM'), 'CREDITS', 5)
#     assert set(query) == possibles

# ########################################
# #               Partie 4               #
# ########################################

# def test_update_int():
#     db = get_programme_db()
#     entry = COURSES[0] | {'CREDITS': 0}
#     db.add_entry('cours', entry)
#     assert db.select_entry('cours', ('CREDITS',), 'id', 1) == 0
#     # oopsie: should be 10 ECTS
#     updated = db.update_entries(
#         'cours',
#         'id', 1,
#         'CREDITS', 10
#     )
#     assert updated
#     assert db.select_entry('cours', ('CREDITS',), 'id', 1) == 10

# def test_update_shorter_string():
#     db = get_programme_db()
#     db.add_entry('cours', COURSES[1])
#     db.update_entries(
#         'cours',
#         'NOM', 'Fonctionnement des ordinateurs',
#         'NOM', 'FDO'
#     )
#     assert db.select_entry('cours', ('NOM',), 'id', 1) == 'FDO'

# def test_update_longer_string():
#     db = get_programme_db()
#     db.add_entry(
#         'cours',
#         {'MNEMONIQUE': 205, 'NOM': 'CFN',
#          'COORDINATEUR': 'Maarten Jansen', 'CREDITS': 5}
#     )
#     correct_name = 'Calcul Formel et Numérique'
#     # Requires reallocation
#     db.update_entries(
#         'cours',
#         'MNEMONIQUE', 205,
#         'NOM', correct_name
#     )
#     assert db.select_entry('cours', ('NOM',), 'id', 1) == correct_name

# def test_update_wrong_type():
#     db = get_programme_db()
#     db.add_entry(
#         'cours',
#         {'MNEMONIQUE': 205, 'NOM': 'CFN',
#          'COORDINATEUR': 'Maarten Jansen', 'CREDITS': 5}
#     )
#     with pytest.raises(ValueError):
#         db.update_entries('cours', 'CREDITS', 5, 'NOM', 205)

# def test_id_preserved_after_update():
#     db = get_programme_db()
#     fill_courses(db)
#     f103_id = db.select_entry('cours', ('id',), 'MNEMONIQUE', 103)
#     db.update_entries('cours', 'CREDITS', 10, 'NOM', '')
#     assert db.select_entry('cours', ('id',), 'MNEMONIQUE', 103) == f103_id

# def test_delete_entries():
#     db = get_programme_db()
#     fill_courses(db)
#     db.delete_entries('cours', 'CREDITS', 5)
#     expected = [
#         course | {'id': i+1}
#         for i, course in enumerate(COURSES)
#         if course['CREDITS'] != 5
#     ]
#     assert db.get_complete_table('cours') == expected

# def test_resize_after_delete():
#     db = get_programme_db()
#     fill_courses(db)
#     size = _get_table_size('programme/cours.table')
#     db.delete_entries('cours', 'CREDITS', 5)
#     assert _get_table_size('programme/cours.table') < size

# def _get_table_size(p: str) -> int:
#     from binary import BinaryFile
#     with open(p, 'rb') as f:
#         return BinaryFile(f).get_size()

# def test_insert_after_delete():
#     from database import FieldType
#     db = get_empty_db('test_db')
#     db.create_table('table', ['a', FieldType.INTEGER])
#     for i in range(10):
#         db.add_entry('table', {'a': i})
#     db.delete_entries('table', 'a', 5)
#     size = _get_table_size('test_db/table.table')
#     db.add_entry('table', {'a': 5})
#     assert _get_table_size('test_db/table.table') == size

# def test_size_after_delete():
#     db = get_programme_db()
#     fill_courses(db)
#     db.delete_entries('cours', 'CREDITS', 5)
#     assert db.get_table_size('cours') == len([
#         course for course in COURSES if course['CREDITS'] != 5
#     ])

# def test_delete_wrong_type():
#     db = get_programme_db()
#     fill_courses(db)
#     with pytest.raises(ValueError):
#         db.delete_entries('cours', 'CREDITS', 'Programmation')

# ########################################
# #               Partie 5               #
# ########################################

# INPUTS = [
#     '',
#     '''open(programme)
# ''',
#     '''open(programme)
# create_table(cours,MNEM=INTEGER,NOM=STRING,COORD=STRING,CRED=INTEGER)
# list_tables()
# ''',
#     '''open(programme)
# create_table(cours,MNEM=INTEGER,NOM=STRING,COORD=STRING,CRED=INTEGER)
# delete_table(cours)
# list_tables()
# ''',
#     '''open(programme)
# create_table(cours,MNEM=INTEGER,NOM=STRING,COORD=STRING,CRED=INTEGER)
# insert_to(cours,MNEM=101,NOM="Progra",CRED=10,COORD="T. Massart")
# insert_to(cours,MNEM=102,NOM="FDO",CRED=5,COORD="G. Geeraerts")
# insert_to(cours,MNEM=103,NOM="Algo I",CRED=10,COORD="O. Markowitch")
# insert_to(cours,MNEM=105,NOM="LDP I",CRED=5,COORD="C. Petit")
# insert_to(cours,MNEM=106,CRED=5,NOM="Projet I",COORD="G. Joret")
# from_if_get(cours,CRED=5,MNEM)
# ''',
#     '''open(programme)
# create_table(cours,MNEM=INTEGER,NOM=STRING,COORD=STRING,CRED=INTEGER)
# insert_to(cours,MNEM=101,NOM="Progra",CRED=10,COORD="T. Massart")
# insert_to(cours,MNEM=102,NOM="FDO",CRED=5,COORD="G. Geeraerts")
# insert_to(cours,MNEM=103,NOM="Algo I",CRED=10,COORD="O. Markowitch")
# insert_to(cours,MNEM=105,NOM="LDP I",CRED=5,COORD="C. Petit")
# insert_to(cours,MNEM=106,CRED=5,NOM="Projet I",COORD="G. Joret")
# from_if_get(cours,CRED=5,*)
# ''',
#     '''open(programme)
# create_table(cours,MNEM=INTEGER,NOM=STRING,COORD=STRING,CRED=INTEGER)
# insert_to(cours,MNEM=101,NOM="Progra",CRED=10,COORD="T. Massart")
# insert_to(cours,MNEM=102,NOM="FDO",CRED=5,COORD="G. Geeraerts")
# insert_to(cours,MNEM=103,NOM="Algo I",CRED=10,COORD="O. Markowitch")
# insert_to(cours,MNEM=105,NOM="LDP I",CRED=5,COORD="C. Petit")
# insert_to(cours,MNEM=106,CRED=5,NOM="Projet I",COORD="G. Joret")
# from_delete_where(cours,MNEM=105)
# from_if_get(cours,CRED=5,MNEM)
# ''',
#     '''open(programme)
# create_table(cours,MNEM=INTEGER,NOM=STRING,COORD=STRING,CRED=INTEGER)
# insert_to(cours,MNEM=101,NOM="Progra",CRED=10,COORD="T. Massart")
# from_update_where(cours,id=1,CRED=0)
# from_if_get(cours,CRED=0,MNEM)
# '''
# ]

# INPUTS = [
#     (data + 'quit') for data in INPUTS
# ]

# OUTPUTS = [
#     '',
#     '',
#     'cours',
#     '',
#     '102 105 106'.replace(' ', '\n'),
#     '''(102, 'FDO', 'G. Geeraerts', 5)
# (105, 'LDP I', 'C. Petit', 5)
# (106, 'Projet I', 'G. Joret', 5)''',
#     '102 106'.replace(' ', '\n'),
#     '101',
# ]

# def test_script_interactive():
#     from subprocess import Popen, PIPE
#     for data, expected in zip(INPUTS, OUTPUTS):
#         _ = get_empty_db('programme')
#         with Popen(['python3', 'uldb.py'], stdin=PIPE, stdout=PIPE, text=True) as process:
#             output, _ = process.communicate(data)
#             assert process.poll() is not None
#             output = output.replace('uldb:: ', '').strip()
#             if output != expected:
#                 print(f'Tested code:\n\n{data}\n\nExpected:\n{expected}\n\nbut got:\n{output}')
#                 assert False

# def test_script_param():
#     from subprocess import run
#     expected = '''cours
# 102
# 105
# 106
# (2, 102)
# (4, 105)
# (5, 106)
# (102, 'FDO', 'G. Geeraerts', 5)
# (105, 'LDP I', 'C. Petit', 5)
# (106, 'Projet I', 'G. Joret', 5)
# 101
# 103
# 101
# 101
# 101'''
#     _ = get_empty_db('programme')
#     del _
#     process = run(['python3', 'uldb.py', 'script.uldb'], check=True, capture_output=True, text=True)
#     assert process.stdout.strip() == expected
