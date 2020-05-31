from flask import Flask
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import numpy as np
import requests
import subprocess
import json


app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.ImageRecognitionDB
users = db["Users"]


def user_exists(username):
    if users.count_documents({"Username": username}) == 0:
        return False
    else:
        return True


def verify_pw(username, password):
    if not user_exists(username):
        return False

    hashed_pw = users.find({"Username": username})[0]["Password"]
    if bcrypt.hashpw(password.encode('utf'), hashed_pw) == hashed_pw:
        return True
    else:
        return False


def count_tokens(username):
    tokens = users.find({"Username": username})[0]["Tokens"]
    return tokens

class Register(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]

        if user_exists(username):
            ret_json = {
                'status': 301,
                'message': "Username already register"
            }
            return ret_json, 301

        hash_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        users.insert_one({
            "Username": username,
            "Password": hash_pw,
            "Tokens": 4
        })

        ret_json = {
            'status': 200,
            'message': "You've successfully signed up to the API"
        }
        return ret_json, 200


class Refill(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["admin_password"]
        refill_amount = posted_data["refill_amount"]

        if not user_exists(username):
            ret_json = {
                'status': 301,
                'message': "Invalid username"
            }
            return ret_json, 301

        correct_pw = '123abc'

        if not password == correct_pw:
            ret_json = {
                'status': 302,
                'message': 'Invalid admin password'
            }
            return ret_json, 302

        current_tokens = count_tokens(username)
        users.update(
            {"Username": username},
            {
                "$set": {"Tokens": current_tokens + refill_amount}
            }
        )

        ret_json = {
            'status': 200,
            'message': "Refilled Tokens",
            'tokens': current_tokens + refill_amount
        }
        return ret_json, 200


class Classify(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["admin_password"]
        url = posted_data["url"]

        correct_pw = verify_pw(username, password)
        if not correct_pw:
            ret_json = {
                'status': 302,
                'message': 'Incorrect username or password'
            }
            return ret_json, 302

        num_tokens = count_tokens(username)
        if num_tokens <= 0:
            ret_json = {
                'status': 301,
                'message': 'Not enough tokens'

            }
            return ret_json, 301


        r = requests.get(url)
        ret_json = {}
        with open("temp.jpg", "wb") as f:
            f.write(r.content)
            proc = subprocess.Popen('python classify_image.py --model_dir =. --image_file =./temp.jpg')
            proc.communicate()[0]
            proc.wait()
            with open('text.txt', 'wb') as g:
                ret_json = json.load(g)

        users.update({
            "Username": username},
            {"$set": {
                "Tokens": num_tokens - 1
            }
            }
        )

        return ret_json, 200


api.add_resource(Register, '/register')
api.add_resource(Classify, '/classify')
api.add_resource(Refill, '/refill')

if __name__ == '__main__':
    app.run(host='0.0.0.0')