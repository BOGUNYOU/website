#!usr/bin/python
# _*_ coding:utf-8 _*_
'''
Configuration
'''
import config_default
class Dict(dict):
    '''创建Dict类，字典内的key值可以通过类属性进行调用'''
    def __init__(self, names=(), values=(), **kwargs):
        super(Dict, self).__init__(**kwargs)
        for k, v in zip(names, values):
            self[k] = v
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)
    def __setattr__(self, key, value):
        self[key] = value
def merage(defaults, ovrride):
    '''遍历默认配置，并用部署时的配置替换默认配置'''
    dirs={}
    for k,v in defaults.iteritems():
        if k in ovrride:
            if isinstance(v, dict):
                dirs[k] = merage(v , ovrride[k])
            else:
                dirs[k] = ovrride[k]
        else:
            dirs[k] = v
    return dirs
def toDict(d):
    '''通过该函数可以将配置文件内的字典转换为累的属性形式进行访问，更利于调用'''
    D = Dict()
    for k, v in d.iteritems():
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D
config = config_default.configs
try:
    import ovriride_config
    config = merage(config, ovriride_config.configs)
except ImportError:
    pass
config = toDict(config)