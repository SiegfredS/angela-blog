from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
from sqlalchemy import Table, Column, Integer, ForeignKey
import random


#CONFIGURE APP
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

#LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(int(user_id))

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

#PARENT
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(1000), nullable=False)
    # like list of BlogPost object attached to each user
    # "author" == author property in blogpost class
    posts = relationship("BlogPost", back_populates="post_author")
    user_comments = relationship("Comment", back_populates="comment_author")


#CHILD
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, ForeignKey("users.id"))  # parent_id
    # create reference to user object, "posts" == post property in user class
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    post_author = relationship("User", back_populates="posts")
    post_comments = relationship("Comment", back_populates="parent_post")
    # author_id == Foreign Key, "users.id" == tablename of user


#ANOTHER CHILD
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    parent_post_id = db.Column(db.Integer, ForeignKey("blog_posts.id"))
    author_id = db.Column(db.Integer, ForeignKey("users.id"))
    # avatar = db.Column(db.Text, nullable=False) DI ATA NEED
    comment_author = relationship("User", back_populates="user_comments")
    parent_post = relationship("BlogPost", back_populates="post_comments")
    text = db.Column(db.Text, nullable=False) #String max = 255 chars, text max = 30,000 chars.

# db.create_all()
# FIRST RUN ONLY: CREATING DB & relationships din
# db.create_all()

# new_blog_post = BlogPost(
#     id=1,
#     author_id=1,
#     title="title",
#     subtitle="subtitle",
#     date="July 20 2022",
#     body="body",
#     img_url="https://www.howtogeek.com/wp-content/uploads/2018/06/shutterstock_1006988770.png?height=200p&trim=2,2,2,2"
# )
# db.session.add(new_blog_post)
# db.session.commit()
#DECORATORS

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            current_user_id = current_user.id
        except AttributeError:
            current_user_id = 0
        if current_user_id != 1 or current_user.is_anonymous:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

def generate_avatar():
    ratings = ["g", "pg", "r", "x"]
    default = ["mp", "identicon", "monsterid", "wavatar", "retro", "robohash"]
    random_rating = random.choice(ratings)
    random_default = random.choice(default)
    random_avatar = Gravatar(
        app=app,
        size=100,
        rating=random_rating,
        default=random_default
    )
    return random_avatar

#CODE

@app.route('/')
def get_all_posts():
    posts = db.session.query(BlogPost).all()
    is_admin = 0
    try:
        if current_user.id == 1:
            is_admin = 1
    except AttributeError:
        pass
    return render_template("index.html",
                           all_posts=posts,
                           logged_in=current_user.is_authenticated,
                           is_admin=is_admin)


@app.route('/register', methods=["GET", "POST"])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        form_data = {item: value.data for (item,
                                           value) in register_form._fields.items() if item not in ["submit",
                                                                                                   "csrf_token"]}
        #new_user = User(**form_data) pwede to
        new_user = User()
        for arg, value in form_data.items():
            if arg in User.__table__.columns and arg != "password":
                setattr(new_user, arg, value)
            elif arg == "password":
                hashed_password = generate_password_hash(password=value,
                                                         method="pbkdf2:sha256",
                                                         salt_length=8)
                setattr(new_user, arg, hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            flash(message="Email already taken. Login instead")
            return redirect(url_for("login"))
        else:
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=register_form, logged_in=current_user.is_authenticated)


@app.route('/login', methods=["POST", "GET"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user_trying_to_login = db.session.query(User).filter_by(email=login_form.data.get("email")).first()
        if user_trying_to_login:
            if check_password_hash(user_trying_to_login.password, login_form.data.get("password")):
                login_user(user_trying_to_login)
                return redirect(url_for("get_all_posts"))
            else:
                flash(message="Wrong Password")
        else:
            flash(message="User email does not exist")
    return render_template("login.html", form=login_form, logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CommentForm()
    comments = db.session.query(Comment).filter_by(parent_post_id=post_id)
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                comment_author=current_user,
                parent_post=requested_post,
                text=comment_form.data.get("comment")
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id=post_id))
        else:
            flash(message="Please login to leave a comment")
            return redirect(url_for("login"))
    return render_template("post.html",
                           post=requested_post,
                           form=comment_form,
                           logged_in=current_user.is_authenticated,
                           comments=comments,
                           gravatar=generate_avatar())


@app.route("/about")
def about():
    try:
        print(current_user.name)
    except:
        print()
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    try:
        print(current_user.name)
    except:
        print()
    return render_template("contact.html", logged_in=current_user.is_authenticated)



@app.route("/new-post", methods=["GET","POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            post_author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)



@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.post_author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id, logged_in=current_user.is_authenticated))

    return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated)



@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
