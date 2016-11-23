#!usr/bin/python
#_*_ coding:utf-8 _*_
from models import Blogs,Users
from transwraps import db
import logging
db.create_engine(user='root', password='znbxd@1992', database='awesome')
a = Users(name= 'tset',password= '111111')
a.insert()