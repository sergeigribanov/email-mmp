from emmp.auth import auth
from emmp.send import send
from emmp.receive import receive
from pyunpack import Archive
import os
import re

if __name__ == '__main__':
  service = auth()
  q = receive(service, 'after:2020/06/08 before:2020/06/09',
             attachments = True)
  ars = ['.zip', '.gz', '.tar.gz', '.tar', '.rar', '.7z']
  for root, dirs, files in os.walk('downloads'):
        for filename in files:
          flag = any(el in filename for el in ars)
          if flag:
            path = os.path.join(root, filename)
            Archive(path).extractall(root)
          
  print(q)
