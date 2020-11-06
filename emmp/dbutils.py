import datetime

def get_persons(conn, tag):
    cursor = conn.cursor()
    query = '''select 
    last_name,
    first_name,
    email,
    group_number,
    io
    from persons
    where tag="{}"'''.format(tag)
    cursor.execute(query)
    result = dict()
    for row in cursor:
        last_name = row[0]
        first_name = row[1]
        pid = row[2]
        group_number = row[3]
        io = row[4]
        result[pid] = dict()
        result[pid]['last_name'] = last_name
        result[pid]['first_name'] = first_name
        result[pid]['group_number'] = group_number
        result[pid]['io'] = io
        
    return result

def register_sent_options(con, tag, poption):
    pass
