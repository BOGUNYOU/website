#_*_ coding:utf-8 _*_
import time
from transwraps.db import next_id
from transwraps.orm import Model, StringField, BoolenField, FloatField, TextField
class Users(Model):
    __table__ = 'users'
    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(updatable=False, ddl='varchar(50)')
    password = StringField(ddl='varchar(50)')
    admin = BoolenField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(updatable=False, default=time.time)
class Blogs(Model):
    __table__ = 'blogs'
    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(updatable=False, ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)
class Comments(Model):
    __table__ = 'comments'
    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(updatable=False, ddl='varchar(50)')
    user_id = StringField(updatable=False, ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)

'''
    实例化所要创建的表之后，通过实例属性__sql__即可获得所要创建的表的sql语句。
    For example:

    a = Commenttest()
    print a.__sql__()
'''
a = Comments()
b = Users()
c=Blogs()
print a.__sql__()
print b.__sql__()
print c.__sql__()

