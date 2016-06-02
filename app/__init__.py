#!/usr/bin/env python
#
# Copyright 2016 Feei. All Rights Reserved
#
# Author:   Feei <wufeifei@wufeifei.com>
# Homepage: https://github.com/wufeifei/cobra
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the file 'doc/COPYING' for copying permission
#
import ConfigParser
import os
import sys

from flask import Flask
from flask.ext.migrate import MigrateCommand, Migrate
from flask.ext.script import Manager, Server, Option, Command
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.bootstrap import Bootstrap

from utils import log

log.info('Initialization HTTP Server')
reload(sys)
sys.setdefaultencoding('utf-8')

template = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
asset = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates/asset')
web = Flask(__name__, template_folder=template, static_folder=asset)

config = ConfigParser.ConfigParser()
config.read('config')
web.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
web.config['SQLALCHEMY_DATABASE_URI'] = config.get('database', 'mysql')

bootstrap = Bootstrap(web)

db = SQLAlchemy(web)

# just use the migration script's app context when you import the models
# http://stackoverflow.com/questions/33905706/flask-migrate-seemed-to-delete-all-my-database-data
with web.app_context():
    from models import *

migrate = Migrate(web, db)
manager = Manager(web)


class Scan(Command):
    option_list = (
        Option('--target', '-t', dest='target', help='scan target(directory/git repository/svn url/file path)'),
        Option('--pid', '-p', dest='pid', help='scan project id')
    )

    def parse_target(self, target=None):
        if target[len(target) - 4:] == '.git':
            return 'git'
        elif os.path.isdir(target) is True:
            return 'directory'
        elif os.path.isfile(target) is True:
            filename, file_extension = os.path.splitext(target)
            if file_extension in ['.tar.gz', '.rar', '.zip']:
                return 'compress'
            else:
                return 'file'
        elif target[0:7] == 'http://' or target[0:8] == 'https://':
            return 'svn'
        else:
            return False

    def run(self, target=None, pid=None):
        if target is None:
            print("Please set --target param")
            sys.exit()
        target_type = self.parse_target(target)
        if target_type is False:
            print("""
                Git Repository: must .git end
                SVN Repository: can http:// or https://
                Directory: must be local directory
                File: must be single file or tar.gz/zip/rar compress file
                """)
        from engine import static
        s = static.Static()
        if target_type is 'directory':
            s.analyse(target)
        elif target_type is 'compress':
            from utils.decompress import Decompress
            # load an compressed file. only tar.gz, rar, zip supported.
            dc = Decompress(target)
            # decompress it. And there will create a directory named "222_test.tar".
            dc.decompress()
            s.analyse(target)
        elif target_type is 'file':
            s.analyse(target)
        elif target_type is 'git':
            from pickup.GitTools import Git
            g = Git(target, branch='master')
            g.get_repo()
            if g.clone() is True:
                s.analyse(target)
            else:
                print("Git clone failed")
        elif target_type is 'svn':
            print("Not Support SVN Repository")


host = config.get('cobra', 'host')
port = config.get('cobra', 'port')
port = int(port)

manager.add_command('db', MigrateCommand)
manager.add_command('start', Server(host=host, port=port))
manager.add_command('scan', Scan())

from app.controller import route
from app.controller import RulesAdmin

log.info('Cobra HTTP Server Started')