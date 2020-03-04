#!/usr/bin/python3

import sqlite3

schema = {
        'teachers': {
            'id': 'INTEGER PRIMARY KEY',
            'name': 'TEXT',
            'sortable_name':  'TEXT',
            'cu_id': 'CHAR(4)'},
        'sections': {
            'id': 'INTEGER PRIMARY KEY',
            'teacher': 'INTEGER REFERENCES teachers (id)',
            'full_name': 'TEXT',
            'short_name': 'CHAR(4)',
            'time': 'TIME'}, # null : not known
        'students': {
            'id': 'INTEGER PRIMARY KEY',
            'sisid': 'INTEGER',
            'name': 'TEXT',
            'sortable_name': 'TEXT',
            'section': 'INTEGER REFERENCES sections (id)'},
        'allowed_modders': {
            'student': 'INTEGER REFERENCES students(id)',
            'modder': 'TEXT'},
        'assignment_groups': {
            'id': 'INTEGER PRIMARY KEY',
            'name': 'TEXT',
            'type': 'INTEGER'}, # enum: 0: whatever, 1: exam, 2: alt exam, 3: final exam, 4: upload
        'exams': {
            'id': 'INTEGER PRIMARY KEY',
            'quiz_id': 'INTEGER',
            'name': 'TEXT',
            'agroup': 'INTEGER REFERENCES assignment_groups (id)',
            'date': 'DATE',
            'due_at': 'DATE', # Do I want these?
            'unlock_at': 'DATE', # ?
            'lock_at': 'DATE'}, # ?
        'uploads': {
            'id': 'INTEGER PRIMARY KEY',
            'name': 'TEXT',
            'date': 'DATE'},
        'grades': {
            'student': 'INTEGER REFERENCES students (id)',
            'exam': 'INTEGER REFERENCES exams (id)',
            'score': 'INTEGER'}
        }

def create_tables(conn):
    with conn: # commits or rolls back
        for table, fields in schema.items():
            cols = ', '.join(f'{field} {typ}' for field, typ in fields.items())
            conn.execute(f'CREATE TABLE {table} ({cols})')

def list_tables(conn):
    return [t[0] for t in conn.execute('SELECT name FROM sqlite_master WHERE type = "table"')]

conn = sqlite3.connect('coursedata.db')
conn.execute('PRAGMA foreign_keys=ON')
create_tables(conn)
conn.close()

