from models import Users,Blogs,Comments
from transwraps import db
from config import config
import time
s = 'test'
s2 = 'testett'
db.create_engine(**config.db)

time.sleep(1)
print 'down'