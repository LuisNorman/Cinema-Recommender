from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import re

app = Flask(__name__)

app.secret_key = 'secret'

connection = pymysql.connect("localhost", "testuser", "test123", "cinemarecommender")

# @app.route('/')
# def hello_world():
#     return 'Hello World!'

# http://localhost:5000/ - this will be the login page, we need to use both GET and POST requests
@app.route('/', methods=['GET', 'POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if user exists using MySQL
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = %s AND password = %s', (username, password))
        # Fetch one record and return result
        user = cursor.fetchone()
        # If user exists in user table in out database
        if user:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['Id'] = user['Id']
            session['Username'] = user['Username']
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # user doesnt exist or username/password incorrect
            msg = 'Incorrect username/password or user does not exist!'
    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)

# http://localhost:5000/logout - this will be the logout page
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   print("loggedin" in session)
   session.pop('loggedin', None)
   session.pop('Id', None)
   session.pop('Username', None)
   # Redirect to login page
   return redirect(url_for('login'))

# http://localhost:5000/pythinlogin/register - this will be the registration page, we need to use both GET and POST requests
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'Username' in request.form and 'Password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if user exists using MySQL
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = %s', username)
        user = cursor.fetchone()
        # If user exists show error and validation checks
        if user:
            msg = 'User already exists!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password:
            msg = 'Please fill out the form!'
        else:
            # user doesnt exists and the form data is valid, now insert new user into user table
            cursor.execute('INSERT INTO User VALUES (NULL, %s, %s)', (username, password))
            connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

# http://localhost:5000/pythinlogin/home - this will be the home page, only accessible for loggedin users
@app.route('/home')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('home.html', username=session['Username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

# http://localhost:5000/pythinlogin/profile - this will be the profile page, only accessible for loggedin users
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # Check if user is loggedin
    if 'loggedin' in session and request.method == 'GET':
        # We need all the user info for the user so we can display it on the profile page
        connection = pymysql.connect("localhost", "testuser", "test123", "cinemarecommender")
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE id = %s', [session['Id']])
        user = cursor.fetchone()
        # We need to retrieves all movies users has rated for now but later get not rated movies to rate
        cursor.execute('select title, rating from Movie right join Rating on Id = Rating.MovieId and Rating.UserId = %s', session['Id']);
        ratedMovies = cursor.fetchall()
        cursor.execute('select title, id from Movie where Id not in (select Id from Movie full join Rating on Id = Rating.MovieId and Rating.UserId = %s)', session['Id']);
        unratedMovies = cursor.fetchall()
        # Show the profile page with user info
        return render_template('profile.html', user=user, ratedMovies=ratedMovies, unratedMovies=unratedMovies)

    elif request.method == 'POST':
        print(request.form['movieid'])
        movieid = request.form['movieid']
        return redirect(url_for('rate', movieid=movieid))

    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/rate', methods=['GET', 'POST'])
def rate():
    # Check if user is loggedin
    if 'loggedin' in session and request.method == 'GET':
        movieid = request.args.get('movieid')
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('select title, id from Movie where id = %s', movieid);
        movie = cursor.fetchone()
        return render_template('rate.html', movie=movie)

    # POST
    else:
        if 'rating' not in request.form:
            return redirect(url_for('unsuccessful'))

        else:
            rating = request.form['rating']
            movieid = request.form['movieid']
            cursor = connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute('insert into rating values(%s, %s, %s)', (session['Id'], movieid, rating));
            connection.commit()
            return redirect(url_for('success'))

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/unsuccessful')
def unsuccessful():
    return render_template('unsuccessful.html')

if __name__ == '__main__':
    app.run(debug=True)
