import cmd, sys, os
import re
import json
import sqlite3
import argparse
from shutil import copyfile
from random import shuffle
from datetime import datetime, timedelta
from emmp.auth import auth
from emmp.dbutils import get_persons
from emmp.send import send
from emmp.receive import receive
from pyunpack import Archive

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

class MMPExamCli(cmd.Cmd):
    def __init__(self, tag):
        cmd.Cmd.__init__(self)
        self.intro = 'Welcome to MMP exam client!\n'
        self.prompt = '(mmp) '
        self.tag = tag
        print('Mailing tag: {}'.format(self.tag))
        self.messaging_config = 'messages.json'
        self.option_filename_template = 'option-([0-9]+).pdf'
        self.archive_formats = ['.zip', '.gz', '.tar.gz',
                                '.tar', '.rar', '.7z']
        self.conn = sqlite3.connect('database.db')
        self.service = auth()
        self._setup_date_query()
        self._setup_email_templates()

    def emptyline(self):
        return ''

    def do_send_options(self, cc):
        'Sending options to tagged group of students'
        self._send_options(cc)
        
    def do_load_exam_files(self, arg):
        'Getting exam files'
        prefix = os.path.join('downloads', self.tag)
        # query = 'after:2020/06/08 before:2020/06/09'
        receive(self.service, self.date_query,
                prefix, attachments = True)
        self._unzip(prefix)
        self._rename_studfiles(prefix)

    def do_rename(self, arg):
        prefix = os.path.join('downloads', self.tag)
        self._rename_studfiles(prefix)

    def do_load_messages(self, arg):
        'Getting messages'
        # query = 'after:2020/06/08 before:2020/06/09'
        msgs = receive(self.service, self.date_query)
        oks = ['ok', 'Ok', 'oK', 'OK', 'ок', 'Ок', 'оК', 'ОК', 'получил', 'Получил']
        fails = ['fail', 'Fail', 'FAIL']
        noks = 0
        nfails = 0
        for mid in msgs:
            el = msgs[mid]

            isok = False
            isfail = False
            if 'subject' in el:
                isok = isok or any(ok in el['subject'] for ok in oks)
                isfail = isfail or any(fail in el['subject'] for fail in fails)
                
            if 'snippet' in el:
                isok = isok or any(ok in el['snippet'] for ok in oks)
                isfail = isfail or any(fail in el['snippet'] for fail in fails)

            if 'message' in el:
                isok = isok or any(ok in el['message'] for ok in oks)
                isfail = isfail or any(fail in el['message'] for fail in fails)
            
            if isok:
                noks += 1

            if isfail:
                nfails += 1
            
        print('noks = {noks}, nfails = {nfails}'.format(
            noks = noks, nfails = nfails))
                
    def do_send_test(self, cc):
        self._send_test(cc)

    def do_set_results(self, arg):
        'Set results'
        path = 'results_{}.json'.format(self.tag)
        self._set_results()
        
    def do_send_results(self, cc):
        'Send results'
        path = 'results_{}.json'.format(self.tag)
        if not os.path.exists(path):
            self._set_results()
            
        self._send_results(path, cc)

    def do_exit(self, arg):
        'Exiting'
        self.conn.close()
        return True

    def _send_test(self, cc):
        with open(self.messaging_config, 'r') as fl:
            data = json.load(fl)

        subject = data[self.tag]['test_msg']['subject']
        with open(data[self.tag]['test_msg']['body'], 'r') as fl:
            body_template = fl.read()
        
        persons = get_persons(self.conn, self.tag)
        for pid in persons:
            name = '{} {}'.format(
                persons[pid]['last_name'], persons[pid]['first_name'])
            body = body_template.format(name = name)
            send(self.service, pid, subject, body, cc = cc)
            

    def _unzip(self, prefix):
        for root, dirs, files in os.walk(prefix):
            for filename in files:
                flag = any(el in filename
                           for el in self.archive_formats)
                if flag:
                    path = os.path.join(root, filename)
                    Archive(path).extractall(root)
    

    def _new_filename_begin(self, root, persons):
        email = os.path.basename(root)
        if '@' not in email:
            return None
        
        fname_begin = None
        for key in persons:
            if email in key:
                fname_begin = '{lname} {io} {gnum}'.format(
                    lname =  persons[key]['last_name'],
                    io = persons[key]['io'],
                    gnum = persons[key]['group_number'])

        return fname_begin

    def _filetype_case(self, files):
        exts = [os.path.splitext(path)[1] for path in files]
        npdf = exts.count('.pdf')
        nimg = exts.count('.jpg')
        nimg += exts.count('.jpeg')
        if npdf == 1 and nimg == 0:
            return True
        else:
            return False

    def _create_src_dirs(self, prefix):
        self.path_pdfs = os.path.join(prefix, 'pdfs')
        self.path_imgs = os.path.join(prefix, 'imgs')
        if not os.path.exists(self.path_pdfs):
            os.makedirs(self.path_pdfs)

        if not os.path.exists(self.path_imgs):
            os.makedirs(self.path_imgs)
            
    def _copy_studfiles(self, fname_begin, root, files):
            
        if self._filetype_case(files):
            src_filename = [el for el in files if '.pdf' in el][0]
            src = os.path.join(root, src_filename)
            dst = os.path.join(self.path_pdfs, '{}.pdf'.format(fname_begin))
            copyfile(src, dst)
        else:
            src_filenames = [el for el in files
                            if ('.pdf' in el or
                                '.jpg' in el or
                                '.jpeg' in el)]
            for index, src_filename in enumerate(src_filenames):
                src = os.path.join(root, src_filename)
                ext = os.path.splitext(src_filename)[1]
                dst = os.path.join(self.path_imgs, '{} {}{}'.format(
                    fname_begin, index, ext))
                copyfile(src, dst)
                    
    def _rename_studfiles(self, prefix):
        self._create_src_dirs(prefix)
        persons = get_persons(self.conn, self.tag)
        for root, dirs, files in os.walk(prefix):
            n = len(files)
            if n == 0:
                continue

            fname_begin = self._new_filename_begin(root, persons)
            print(fname_begin)
            if fname_begin == None:
                continue

            self._copy_studfiles(fname_begin, root, files)
                
    def _setup_email_templates(self):
        with open(self.messaging_config, 'r') as fl:
            config = json.load(fl)

        self.options_subject = config[self.tag]['send_options']['subject']
        self.results_subject = config[self.tag]['send_results']['subject']
        with open(config[self.tag]['send_options']['body']) as fl:
            self.options_body_template = fl.read()

        with open(config[self.tag]['send_results']['body']) as fl:
            self.results_body_template = fl.read()
        
    def _setup_date_query(self):
        today = datetime.today().strftime('%Y/%m/%d')
        tomorrow = (datetime.today() + timedelta(days=1)).strftime('%Y/%m/%d')
        self.date_query = 'after:{today} before:{tomorrow}'.format(
            today = today, tomorrow = tomorrow)

    def _load_options(self):
        prefix = os.path.join('options', self.tag)
        result = []
        for root, dirs, files in os.walk(prefix):
            for filename in files:
                match = re.match(self.option_filename_template, filename)
                if match:
                    path = os.path.join(root, filename)
                    result.append((int(match.group(1)), path))

        return result
        
    def _set_options(self):
        persons = get_persons(self.conn, self.tag)
        options = self._load_options()
        opts = []
        result = []
        for pid in persons:
            person = persons[pid]
            if len(opts) == 0:
                opts = options.copy()
                shuffle(opts)
            
            opt = opts[0]
            del opts[0]
            result.append({'email' : pid,
                           'name' : '{} {}'.format(
                               person['last_name'],
                               person['first_name']),
                           'option' : opt})

        path = 'options_{}.json'.format(self.tag)
        with open(path, 'w', encoding='utf-8') as fl:
            json.dump(result, fl, indent=4, ensure_ascii=False)
        
    def _send_options_to_person(self, poption, cc):
        option = poption['option']
        body = self.options_body_template.format(
            name = poption['name'],
            option = option[0])
        send(self.service,
             poption['email'],
             self.options_subject, body,
             attachment = option[1], cc = cc)

    def _send_options(self, cc):
        option_config_path = 'options_{}.json'.format(self.tag)
        options = []
        if not os.path.exists(option_config_path):
            self._set_options()

        with open(option_config_path, 'r') as fl:
            options = json.load(fl)
            
        for poption in options:
            try:
                self._send_options_to_person(poption, cc)
            except:
                print('Not sent: {name}, {email}'.format(
                    name = poption['name'], email = poption['email']))

    def _set_results(self):
        persons = get_persons(self.conn, self.tag)
        result = dict()
        result['sent'] = []
        result['not sent'] = []
        for pid in persons:
            io = persons[pid]['io']
            gnum = persons[pid]['group_number']
            lname = persons[pid]['last_name']
            name = '{} {}'.format(
                lname,
                persons[pid]['first_name'])
            filename = '{lname} {io} {gnum}_final.pdf'.format(
                lname = lname, io = io, gnum = gnum)
            path = os.path.join('results', self.tag, filename)

            if os.path.exists(path):
                result['sent'].append({'email' : pid, 'name' : name, 'path' : path})
            else:
                result['not sent'].append({'email' : pid, 'name' : name, 'io' : io})

        path = 'results_{}.json'.format(self.tag)
        with open(path, 'w', encoding='utf-8') as fl:
            json.dump(result, fl, indent=4, ensure_ascii=False)
            
    def _send_results(self, path, cc):
        with open(path, 'r') as fl:
            data = json.load(fl)

        with open('scores_{}.json'.format(self.tag), 'r') as fl:
            scores = json.load(fl)
            
        ns_length = len(data['not sent'])
        ans = True
        if ns_length > 0:
            print(data['not sent'])
            print('There are some persons that will not receive their results (see list above).')
            ans = query_yes_no('Would you like to continue sending results?')
            
        if not ans:
            return
            
        for el in data['sent']:
            print(el['name'], el['email'], el['path'])
            q = re.match('(.*)_final.pdf', os.path.basename(el['path']))
            assert(q != None)
            key = q.group(1)
            score = sum(scores[key])
            value = ''
            cong = ''
            if score < 11:
                value = '<b>Неуд.</b>'
            elif 10 < score < 21:
                value = '<b>Удовл.</b>'
            elif 20 < score < 31:
                value = '<b>Хорошо</b>'
            elif score > 30:
                value = '<b>Отлично</b>'
                cong = '<p><b>Поздравляем!</b></p>'
                
            body = self.results_body_template.format(
                name = el['name'], score = score, value = value, cong = cong)
            send(self.service, el['email'],
                 self.results_subject, body,
                 attachment = el['path'],
                 cc = cc)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--tag', type=str, default='test',
                        help='Mailing tag')
    args = parser.parse_args()
    MMPExamCli(args.tag).cmdloop()
    
