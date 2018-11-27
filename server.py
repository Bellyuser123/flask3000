#!/usr/bin/env python
# -*- coding: utf-8 -*-

#       _                              
#      | |                             
#    __| |_ __ ___  __ _ _ __ ___  ___ 
#   / _` | '__/ _ \/ _` | '_ ` _ \/ __|
#  | (_| | | |  __/ (_| | | | | | \__ \
#   \__,_|_|  \___|\__,_|_| |_| |_|___/ .
#
# A 'Fog Creek'–inspired demo by Kenneth Reitz™

import os
import sqlite3
import pandas as pd

from flask import Flask, request, render_template, jsonify

# Support for gomix's 'front-end' and 'back-end' UI.
app = Flask(__name__, static_folder='public', template_folder='views')

# Set the app secret key from the secret environment variables.
app.secret = os.environ.get('SECRET')

# Dream database. Store dreams in memory for now. 
DREAMS = ['Python. Python, everywhere.']


DBNAME = 'database.db'

def bootstrap_db():

  if os.path.exists(DBNAME):
    os.remove(DBNAME)

  conn = sqlite3.connect(DBNAME)

  c = conn.cursor()

  c.execute('CREATE TABLE dreams (dream text)')

  c.execute('INSERT INTO dreams VALUES (?)', DREAMS)

  # c.execute('SELECT * FROM dreams')

  # print("first dream in db: " + str(c.fetchone()))

  conn.commit()

  conn.close()


def store_dream(dream):
  conn = sqlite3.connect(DBNAME)

  c = conn.cursor()

  dream_dat = [dream,]
  
  print("dream data to insert: " + str(dream_dat))

  c.execute("INSERT INTO dreams VALUES (?)", dream_dat)

  conn.commit()

  conn.close()
  
def get_dreams():
  conn = sqlite3.connect(DBNAME)

  c = conn.cursor()

  c.execute('SELECT * FROM dreams')

  ret = c.fetchall()
  
  conn.commit()

  conn.close()  
  
  return ret

@app.after_request
def apply_kr_hello(response):
    """Adds some headers to all responses."""
  
    # Made by Kenneth Reitz. 
    if 'MADE_BY' in os.environ:
        response.headers["X-Was-Here"] = os.environ.get('MADE_BY')
    
    # Powered by Flask. 
    response.headers["X-Powered-By"] = os.environ.get('POWERED_BY')
    return response


@app.route('/')
def homepage():
    """Displays the homepage."""
    return render_template('index.html')
    
@app.route('/dreams', methods=['GET', 'POST'])
def dreams():
    """Simple API endpoint for dreams. 
    In memory, ephemeral, like real dreams.
    """
  
    # Add a dream to the in-memory database, if given. 
    if 'dream' in request.args:
        new_dream = request.args['dream']
        # DREAMS.append(new_dream)
        store_dream(new_dream)
    
    # Return the list of remembered dreams. 
    #return jsonify(DREAMS)
    return jsonify(get_dreams())

if __name__ == '__main__':
    bootstrap_db()
    app.run()