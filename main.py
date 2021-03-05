from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug import secure_filename
from flask_mail import Mail
from datetime import datetime
import json
import os
import math

if 'mail_username' in os.environ:
    mail_username = os.environ.get('mail_username')
else:
    exit('Please pass mail_username in environment variable!')

if 'mail_password' in os.environ:
    mail_password = os.environ.get('mail_password')
else:
    exit('Please pass mail_password in environment variable!')

with open('config.json', 'r') as conf:
    params = json.load(conf)['params']

local_server = True

app = Flask(__name__)
app.secret_key = 'temp-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(dict(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = 465,
    MAIL_USE_SSL = True,
    MAIL_USERNAME = mail_username,
    MAIL_PASSWORD = mail_password
))

mail = Mail(app)

if(local_server):
    app.config["SQLALCHEMY_DATABASE_URI"] = params['local_uri']
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['prod_uri']

db = SQLAlchemy(app)

class Contacts(db.Model):
    '''
    sno, name, email, phone_num, msg, date
    '''
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(25), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)

class Posts(db.Model):
    '''
    sno, title, slug, content, img_file, date
    '''
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(30), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    img_file = db.Column(db.String(15), nullable=False)
    date = db.Column(db.String(12), nullable=True)


@app.route("/")
def home():

    posts = Posts.query.filter_by().all()

    last = math.ceil(len(posts) / params['no_of_post_per_page'])

    # [:params['no_of_post_per_page']]

    page = request.args.get('page')

    if(not str(page).isnumeric()):
        page = 1

    page = int(page)

    #Pagination logic
    #First page
    if(page == 1):
        prev = "#"
        next = "/?page="+str(page+1)

    #Last page
    elif(page == last):
        prev = "/?page="+str(page-1)
        next = "#"

    #Middle page
    else:
        prev = "/?page="+str(page-1)
        next = "/?page="+str(page+1)


    posts = Posts.query.filter_by().all()[(page-1)*params['no_of_post_per_page']:page*params['no_of_post_per_page']]

    


    return render_template("index.html", params=params, posts=posts, prev=prev, next=next)

@app.route("/dashboard", methods=['GET', 'POST'])
def login():

    if 'user' in session and session['user'] == params["admin_username"]:
        posts = Posts.query.filter_by().all()
        return render_template("dashboard.html", params=params, posts=posts)

    if request.method=='POST':
        
        username = request.form.get('username')
        password = request.form.get('password')


        if (username == params["admin_username"] and password == params["admin_password"]):
            session['user'] = username
            posts = Posts.query.filter_by().all()
            return render_template("dashboard.html", params=params, posts=posts)

        # else:
        #     return render_template("login.html", params=params)


    return render_template("login.html", params=params)

@app.route("/about")
def about():
    return render_template("about.html", params=params)

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if(request.method == "POST"):
        '''
        Add entry to the database
        '''
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")

        entry = Contacts(name=name, email=email, phone_num=phone, msg=message, date=datetime.now())
        db.session.add(entry)
        db.session.commit()

        mail.send_message('New message from ' + name,
                        sender=email,
                        recipients=[mail_username],
                        body=message + "\n" + phone
                        )


    return render_template("contact.html", params=params)

@app.route("/post/<string:post_slug>", methods=["GET"])
def get_post(post_slug):

    post = Posts.query.filter_by(slug=post_slug).first()

    return render_template("post.html", params=params, post=post)

@app.route("/edit/<string:sno>", methods=["GET", "POST"])
def edit_post(sno):

    if 'user' in session and session['user'] == params["admin_username"]:
        if request.method == "POST":
            req_title = request.form.get("title")
            req_slug = request.form.get("slug")
            req_content = request.form.get("content")
            req_img_file = request.form.get("img_file")
            req_date = datetime.now()

            # If sno == 0 then add new post, else sno != 0 then edit the post corrosponds with sno
            if sno == '0':
                post = Posts(title=req_title, slug=req_slug, content=req_content, img_file=req_img_file, date=req_date)
                db.session.add(post)
                db.session.commit()

            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = req_title
                post.slug = req_slug
                post.content = req_content
                post.img_file = req_img_file
                post.date = req_date
                db.session.commit()
                return redirect('/edit/'+sno)

    post = Posts.query.filter_by(sno=sno).first()

    return render_template("edit.html", params=params, post=post, sno=sno)


@app.route("/uploader", methods=["GET", "POST"])
def uploader():

    if 'user' in session and session['user'] == params["admin_username"]:
        if request.method == "POST":
            file = request.files["myfile"]
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
            return "Uploaded successfully!"

@app.route("/logout", methods=["GET"])
def logout():
    session.pop('user')
    return redirect('/dashboard')

@app.route("/delete/<string:sno>", methods=["GET", "POST"])
def delete_post(sno):

    if 'user' in session and session['user'] == params["admin_username"]:

        Posts.query.filter_by(sno=sno).delete()
        db.session.commit()
        # post = Posts.query.filter_by(sno=sno).first()
        return redirect('/dashboard')

    post = Posts.query.filter_by(sno=sno).first()

    return render_template("dashboard.html", params=params, post=post)


if __name__ == '__main__':
    app.run(debug=True, port = 5003)