from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import re
import math
import decimal
from operator import itemgetter
from datetime import datetime
import csv

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
        print("login")
        print( user['Id'])
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
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if user exists using MySQL
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = %s', username)
        user = cursor.fetchall()
        # If user exists show error and validation checks
        if user:
            msg = 'User already exists!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password:
            msg = 'Please fill out the form!'
        else:
            cursor.execute("Select max(id) from user")
            id_dict = cursor.fetchone()
            id = id_dict["max(id)"] + 1
            # user doesnt exists and the form data is valid, now insert new user into user table
            cursor.execute('INSERT INTO User VALUES (%s, %s, %s)', (id, username, password))
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
        computePearsonSim()
        # computeItemBasedSim()
        # We need all the user info for the user so we can display it on the profile page
        connection = pymysql.connect("localhost", "testuser", "test123", "cinemarecommender")
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        # print([session['Id']])
        cursor.execute('SELECT * FROM User WHERE id = %s', session['Id'])
        user = cursor.fetchone()
        # We need to retrieves all movies users has rated for now but later get not rated movies to rate
        # cursor.execute('select title, rating from Movie inner join Rating on Id = Rating.MovieId and Rating.UserId = %s', session['Id']);
        cursor.execute("select title, rating from rating inner join movie on movieid = movie.id where userid = %s", session['Id'])
        ratedMovies = cursor.fetchall()
        cursor.execute('select title, id from Movie where Id not in (select Id from Movie full join Rating on Id = Rating.MovieId and Rating.UserId = %s)', session['Id']);
        unratedMovies = cursor.fetchall()
        # Show the profile page with user info
        return render_template('profile.html', user=user, ratedMovies=ratedMovies, unratedMovies=unratedMovies)

    elif request.method == 'POST':
        # print(request.form['movieid'])
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

def computePearsonSim():
    pearson_similarities = {}

    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("select avg(rating) as avg_rating from rating where userid = %s", session['Id'])
    rating_dict = cursor.fetchone()
    target_avg_rating = rating_dict['avg_rating']

    cursor.execute("select * from rating where userid = %s", session['Id'])
    target_user_ratings = cursor.fetchall()
    cursor.execute("select id from user")
    id_arr = cursor.fetchall()

    # Loop through every user except target
    # Compute similarity on target and current user ratings
    for current_id in id_arr :
        # Ensure we do not compute similarity on target user
        if current_id["id"] != session["Id"] :
            # Get the current user's ratings and avg rating
            cursor.execute("select * from rating where userid = %s", current_id["id"])
            current_user_ratings = cursor.fetchall()
            cursor.execute("select avg(rating) as avg_rating from rating where userid = %s", current_id['id'])
            rating_dict = cursor.fetchone()
            current_avg_rating = rating_dict['avg_rating']
            # initialize variables used to compute the similarity
            AA = 0
            BB = 0
            num = 0
            ## For every target user's ratings, we loop through the current user's rating and find if they have rated that movie
            for target_rating in target_user_ratings :
                for current_rating in current_user_ratings:
                    # if user has rated movie, we can compute and aggregate the values to compute the similarity
                    if (target_rating["MovieId"] == current_rating["MovieId"]):
                        A = ((target_rating["Rating"]) - target_avg_rating)
                        B = ((current_rating["Rating"]) - current_avg_rating)
                        num = num + (A*B)
                        AA = AA + A * A
                        BB = BB + B * B
            # Once we aggregated all the values on numerator and denominator, we can divide them to get our similarity
            den = math.sqrt(AA*BB)
            num = decimal.Decimal(num)
            den = decimal.Decimal(den)
            # Must check if denominator = 0 / No similarity so we don't get an error
            if den != 0:
                pearson_similarities[current_id["id"]] = num/den
            else:
                pearson_similarities[current_id["id"]] = decimal.Decimal(0)

    pearson_similarities = sorted(pearson_similarities.items(), key=itemgetter(1), reverse=True)
    # print(pearson_similarities)
    # computePredictions(pearson_similarities)
    return pearson_similarities;

@app.route('/userbased', methods=['GET'])
def computePredictions():
    similarities = computePearsonSim()
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("select avg(rating) as avg_rating from rating where userid = %s", session['Id'])
    rating_dict = cursor.fetchone()
    target_avg_rating = rating_dict['avg_rating']
    cursor.execute("select * from rating where userid <> %s", session['Id'])
    ratings = cursor.fetchall()

    cursor.execute("select id, title from movie")
    movies = cursor.fetchall()
    total_movies = cursor.rowcount
    m=0
    recommended_movies = []
    for movie in movies:
        movieid = movie["id"]
        cursor.execute("select * from rating where UserId = %s and MovieId = %s", (session['Id'], movieid))
        target_seen = cursor.rowcount
        if target_seen > 0:
            print("target user rated movie")
        else:
            if m == 50:
                print("Finished")
                break
            m=m+1
            i=0
            num = 0
            den = 0
            for x, y in similarities:
                if i == 3:
                    break
                else:
                    #check if similar user has rated movie
                    # if so compute and store prediction
                    cursor.execute("select * from rating where UserId = %s and MovieId = %s", (str(x), movieid))
                    result = cursor.fetchone()
                    current_seen = cursor.rowcount
                    if current_seen > 0:
                        current_rating = result["Rating"]
                        cursor.execute("select avg(rating) as avg_rating from rating where userid = %s",
                                       str(x))
                        rating = cursor.fetchone()
                        current_avg_rating = rating["avg_rating"]
                        num = num + ((result["Rating"]-current_avg_rating)*y)
                        den = den + y
                        i = i + 1
            if den == 0:
                score = target_avg_rating + 0
            else:
                score = target_avg_rating + (num/den)
            recommendation = (movie["title"], score)
            recommended_movies.append(recommendation)
    recommended_movies = sorted(recommended_movies, key=itemgetter(1), reverse=True)
    # print(recommended_movies)
    return render_template('userbased.html', recommended_movies=recommended_movies)

similarities = {}


# Objective: Retrieve the similarities of every movie to one another
def computeItemBasedSim():
    now = datetime.now()

    start_time = now.strftime("%H:%M:%S")

    similarities = {}
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("select * from movie")
    movies = cursor.fetchall()
    movieCount = cursor.rowcount
    movieTitleDict = {}

    # Nestedly loop through every movie
    i=0
    for movie1 in movies:
        # movie1 = movies[i]      .
        # if i == 2300:
        #     break
        # i = i+1
        currentSimilarities = {}
            # Set up the data structures to compute the similarity and hold the movie information
        for movie2 in movies:
            if movie1["Id"] != movie2["Id"]:
                a = 0
                b = 0
                num = 0

                # if the movies have the same genre, we aggregate 1 to the numerator and add 1 to the distance of movie1 and movie2
                if str(movie1["Action"]) == "1" and str(movie2["Action"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                # if one of the movies have the specific genre, we can add 1 to its distance and nothing the numerator bc it cancels out when you multiply against a non genre
                elif str(movie1["Action"]) == "None" and str(movie2["Action"]) == "1":
                    b = b + 1
                elif str(movie1["Action"]) == "1" and str(movie2["Action"]) == "None":
                    a = a + 1

                if str(movie1["Adventure"]) == "1" and str(movie2["Adventure"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Adventure"]) == "None" and str(movie2["Adventure"]) == "1":
                    b = b + 1
                elif str(movie1["Adventure"]) == "1" and str(movie2["Adventure"]) == "None":
                    a = a + 1

                if str(movie1["Animation"]) == "1" and str(movie2["Animation"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Animation"]) == "None" and str(movie2["Animation"]) == "1":
                    b = b + 1
                elif str(movie1["Animation"]) == "1" and str(movie2["Animation"]) == "None":
                    a = a + 1

                if str(movie1["Children"]) == "1" and str(movie2["Children"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Children"]) == "None" and str(movie2["Children"]) == "1":
                    b = b + 1
                elif str(movie1["Children"]) == "1" and str(movie2["Children"]) == "None":
                    a = a + 1

                if str(movie1["Comedy"]) == "1" and str(movie2["Comedy"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Comedy"]) == "None" and str(movie2["Comedy"]) == "1":
                    b = b + 1
                elif str(movie1["Comedy"]) == "1" and str(movie2["Comedy"]) == "None":
                    a = a + 1

                if str(movie1["Crime"]) == "1" and str(movie2["Crime"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Crime"]) == "None" and str(movie2["Crime"]) == "1":
                    b = b + 1
                elif str(movie1["Crime"]) == "1" and str(movie2["Crime"]) == "None":
                    a = a + 1

                if str(movie1["Documentary"]) == "1" and str(movie2["Documentary"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Documentary"]) == "None" and str(movie2["Documentary"]) == "1":
                    b = b + 1
                elif str(movie1["Documentary"]) == "1" and str(movie2["Documentary"]) == "None":
                    a = a + 1

                if str(movie1["Drama"]) == "1" and str(movie2["Drama"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Drama"]) == "None" and str(movie2["Drama"]) == "1":
                    b = b + 1
                elif str(movie1["Drama"]) == "1" and str(movie2["Drama"]) == "None":
                    a = a + 1

                if str(movie1["Fantasy"]) == "1" and str(movie2["Fantasy"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Fantasy"]) == "None" and str(movie2["Fantasy"]) == "1":
                    b = b + 1
                elif str(movie1["Fantasy"]) == "1" and str(movie2["Fantasy"]) == "None":
                    a = a + 1

                if str(movie1["Film_Noir"]) == "1" and str(movie2["Film_Noir"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Film_Noir"]) == "None" and str(movie2["Film_Noir"]) == "1":
                    b = b + 1
                elif str(movie1["Film_Noir"]) == "1" and str(movie2["Film_Noir"]) == "None":
                    a = a + 1

                if str(movie1["Horror"]) == "1" and str(movie2["Horror"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Horror"]) == "None" and str(movie2["Horror"]) == "1":
                    b = b + 1
                elif str(movie1["Horror"]) == "1" and str(movie2["Horror"]) == "None":
                    a = a + 1

                if str(movie1["Musical"]) == "1" and str(movie2["Musical"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Musical"]) == "None" and str(movie2["Musical"]) == "1":
                    b = b + 1
                elif str(movie1["Musical"]) == "1" and str(movie2["Musical"]) == "None":
                    a = a + 1

                if str(movie1["Mystery"]) == "1" and str(movie2["Mystery"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Mystery"]) == "None" and str(movie2["Mystery"]) == "1":
                    b = b + 1
                elif str(movie1["Mystery"]) == "1" and str(movie2["Mystery"]) == "None":
                    a = a + 1

                if str(movie1["Romance"]) == "1" and str(movie2["Romance"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Romance"]) == "None" and str(movie2["Romance"]) == "1":
                    b = b + 1
                elif str(movie1["Romance"]) == "1" and str(movie2["Romance"]) == "None":
                    a = a + 1

                if str(movie1["Sci_Fi"]) == "1" and str(movie2["Sci_Fi"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Sci_Fi"]) == "None" and str(movie2["Sci_Fi"]) == "1":
                    b = b + 1
                elif str(movie1["Sci_Fi"]) == "1" and str(movie2["Sci_Fi"]) == "None":
                    a = a + 1

                if str(movie1["Thriller"]) == "1" and str(movie2["Thriller"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Thriller"]) == "None" and str(movie2["Thriller"]) == "1":
                    b = b + 1
                elif str(movie1["Thriller"]) == "1" and str(movie2["Thriller"]) == "None":
                    a = a + 1

                if str(movie1["War"]) == "1" and str(movie2["War"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["War"]) == "None" and str(movie2["War"]) == "1":
                    b = b + 1
                elif str(movie1["War"]) == "1" and str(movie2["War"]) == "None":
                    a = a + 1

                if str(movie1["Western"]) == "1" and str(movie2["Western"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["Western"]) == "None" and str(movie2["Western"]) == "1":
                    b = b + 1
                elif str(movie1["Western"]) == "1" and str(movie2["Western"]) == "None":
                    a = a + 1

                if str(movie1["IMAX"]) == "1" and str(movie2["IMAX"]) == "1":
                    num = num + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["IMAX"]) == "None" and str(movie2["IMAX"]) == "1":
                    b = b + 1
                    a = a + 1
                    b = b + 1
                elif str(movie1["IMAX"]) == "1" and str(movie2["IMAX"]) == "None":
                    a = a + 1
                    a = a + 1
                    b = b + 1

                # Check if there is no similarity i.e. the numerator == 0 or denominator == 0
                if a*b == 0 or num == 0:
                    currentSimilarities[movie2["Id"]] = 0
                else:
                    # If the movies have similarity, store the movieid and it's similarity value in a temp dictionary
                    currentSimilarities[movie2["Id"]] = num/math.sqrt(a*b)

        # store the current movie similarities in a dictionary
        similarities[movie1["Id"]] = currentSimilarities
        movieTitleDict[movie1["Id"]] = movie1["Title"]

    # Iterate over each nested dictionary and sort it in descending order for easy retrieval
    for x in similarities.keys():
        similarities[x] = sorted(similarities[x].items(), key=itemgetter(1), reverse=True)

    # Add each movie and its similar movies to an excel file
    totalSimList = [[]]
    for x in similarities:
        list = [x]
        temp = similarities[x]
        # print("the most similar movies for " + str(movieTitleDict[x]) +" are: ")
        for y in temp:
            movieId = y[0]
            movieTitle = movieTitleDict[movieId]
            list.append(movieTitle)
            # print("Sim:" +str(movieTitle))
        totalSimList.append(list)

    # with open('item_based_recommendations.csv', mode='w') as item_based_recommendations:
    csvfile = open('item_based_recommendations.csv', 'w', newline='')
    obj = csv.writer(csvfile)
    for currentSimList in totalSimList:
        obj.writerow(currentSimList)
    csvfile.close()

    now = datetime.now()

    end_time = now.strftime("%H:%M:%S")
    print("start time: " + str(start_time))
    print("end time: " + str(end_time))

@app.route('/itembased', methods=['GET'])
def getItemBasedPredictions():

    # get all the target user's ratings
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("select * from rating where userid = %s", session["Id"])
    target_ratings = cursor.fetchall()
    r_count = cursor.rowcount
    alpha = 20/r_count
    recommended_movies = {}
    with open('item_based_recommendations.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for rating_dict in target_ratings:
            movieid = rating_dict["MovieId"]
            rating = rating_dict["Rating"]
            i=0
            for row in reader:
                if row != []:
                    if str(row[0]) == str(movieid):
                        j=0
                        for col in row:
                            if j != 0:
                                recommended_movies[str(col)] = int(rating)
                                if i == alpha:
                                    break;
                                i = i + 1
                            j = j + 1
                        break;

    recommended_movies = sorted(recommended_movies.items(), key=itemgetter(1), reverse=True)
    return render_template('itembased.html', recommended_movies=recommended_movies)

if __name__ == '__main__':
    app.run(debug=True)