import datetime
import json
import os.path
import re
from random import shuffle

from emmp.dbutils import get_persons
from emmp.receive import receive
from emmp.send import send


def send_results(conn, service, tag):
    prefix = "results"
    for root, dirs, files in os.walk(prefix):
        for filename in files:
            lst = filename.split(" ")
            last_name = lst[0]
            # print(last_name)
            group_num = int(lst[2][0:5])
            cursor = conn.cursor()
            query = """select email, first_name from persons where
            last_name="{last_name}" and 
            group_number={group_num}""".format(
                last_name=last_name, group_num=group_num
            )
            cursor.execute(query)
            path = os.path.join(root, filename)
            email, first_name = cursor.fetchone()
            with open("messages.json", "r") as fl:
                config = json.load(fl)

            subject = config[tag]["send_results"]["subject"]
            with open(config[tag]["send_results"]["body"]) as fl:
                body_template = fl.read()

            body = body_template.format(name="{} {}".format(
                last_name, first_name))
            print(last_name, email, path)
            send(service, email, subject, body, attachment=path)
