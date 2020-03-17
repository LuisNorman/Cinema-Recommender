from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import re
import math
import decimal
from operator import itemgetter
from datetime import datetime
import csv
from sklearn.model_selection import train_test_split
import numpy

app = Flask(__name__)

app.secret_key = 'secret'

connection = pymysql.connect("localhost", "testuser", "test123", "cinemarecommender")
connection.autocommit(True)

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
        # We need all the user info for the user so we can display it on the profile page
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE id = %s', session['Id'])
        user = cursor.fetchone()
        # We need to retrieves all movies users has rated for now but later get not rated movies to rate
        cursor.execute("select title, rating from rating inner join movie on movieid = movie.id where userid = %s", session['Id'])
        ratedMovies = cursor.fetchall()
        cursor.execute('select title, id from Movie where Id not in (select Id from Movie full join Rating on Id = Rating.MovieId and Rating.UserId = %s)', session['Id']);
        unratedMovies = cursor.fetchall()
        # Show the profile page with user info
        return render_template('profile.html', user=user, ratedMovies=ratedMovies, unratedMovies=unratedMovies)

    elif request.method == 'POST':
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
    # create  dictionary to store every movie as the key and its similar movies in decreasing order as the values
    # this allows for easy lookup of the user and then scan for similar users
    pearson_similarities = {}

    # set up sql cursor
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    # retrieve the target user's avg rating to compute pearson correlation
    cursor.execute("select avg(rating) as avg_rating from rating where userid = %s", session['Id'])
    rating_dict = cursor.fetchone()
    target_avg_rating = rating_dict['avg_rating']

    # retrieve the ids of every user to later compute pearson correlation
    cursor.execute("select * from rating where userid <> %s", session['Id'])
    target_user_ratings = cursor.fetchall()
    cursor.execute("select id from user")
    id_arr = cursor.fetchall()

    # Loop through every user except target
    # Compute similarity on target and current user ratings
    for current_id in id_arr:
        # Ensure we do not compute similarity on target user
        if current_id["id"] != session["Id"]:

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

    # sort the similarities for easy searching
    pearson_similarities = sorted(pearson_similarities.items(), key=itemgetter(1), reverse=True)
    return pearson_similarities;

@app.route('/userbased', methods=['GET'])
def computePredictions():
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    # check if user has rated movies
    # if not, display "invalid" page
    cursor.execute('select count(*) as count from rating where userid = %s', (session['Id']))
    rating_count = cursor.fetchone()
    if int(rating_count['count']) == 0:
        return render_template('invalid.html')

    # Keep track of how long it runs
    now = datetime.now()
    print("starting")
    start_time = now.strftime("%H:%M:%S")

    # Compute the similarities
    similarities = computePearsonSim()

    cursor.execute("select avg(rating) as avg_rating from rating where userid = %s", session['Id'])
    rating_dict = cursor.fetchone()
    target_avg_rating = rating_dict['avg_rating']
    cursor.execute("select id, title from movie")
    movies = cursor.fetchall()
    m = 0
    recommended_movies = []
    for movie in movies:
        movieid = movie["id"]
        cursor.execute("select * from rating where UserId = %s and MovieId = %s", (session['Id'], movieid))
        target_seen = cursor.rowcount
        if target_seen > 0:
            print("target user rated movie")
        else:
            # if m == 50:
            #     print("Finished")
            #     break
            m = m + 1
            i = 0
            num = 0
            den = 0
            for x, y in similarities:
                if i == 3:
                    break
                else:
                    # check if similar user has rated movie
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
                        num = num + ((decimal.Decimal(result["Rating"]) - decimal.Decimal(current_avg_rating)) * y)
                        den = den + y
                        i = i + 1

            if round(den,4) == 0:
                score = target_avg_rating + 0
            else:
                score = decimal.Decimal(target_avg_rating) + (num/den)

            if score > 5:
                score = 5
            elif score < 0.5:
                score = 0.5
            score = abs(decimal.Decimal(round(score * 2) / 2))
            recommendation = (movie["title"], score)
            recommended_movies.append(recommendation)
    recommended_movies = sorted(recommended_movies, key=itemgetter(1), reverse=True)
    now = datetime.now()
    end_time = now.strftime("%H:%M:%S")
    print("start time: " +str(start_time))
    print("end time: " + str(end_time))
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
    movieTitleDict = {}

    for movie1 in movies:
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
                ### IF IT DOESNT HAVE SIMILARITY, DO NOT ADD IT
                if a*b != 0 and num != 0:
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
        for y in temp:
            movieId = y[0]
            list.append(movieId)
        totalSimList.append(list)

    # write the similarites to csv where column 1 is the movie
    # and column 2 and on are movies that are similar to the movie
    # in column in decreasing order by their similarity values
    csvfile = open('item_based_recommendations.csv', 'w', newline='')
    obj = csv.writer(csvfile)
    for currentSimList in totalSimList:
        obj.writerow(currentSimList)
    csvfile.close()

    # print time to see how long the function takes
    now = datetime.now()
    end_time = now.strftime("%H:%M:%S")
    print("start time: " + str(start_time))
    print("end time: " + str(end_time))

@app.route('/itembased', methods=['GET'])
def getItemBasedPredictions():
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    # check if user has rated movies
    # if not, display "invalid" page
    cursor.execute('select count(*) as count from rating where userid = %s', (session['Id']))
    rating_count = cursor.fetchone()
    if int(rating_count['count']) == 0:
        return render_template('invalid.html')

    # Store the ids of all the movies for easy look up
    cursor.execute('select * from movie')
    movies = cursor.fetchall()
    titleDict = {}
    for movie in movies:
        titleDict[str(movie["Id"])] = str(movie["Title"])

    # store target user's rating for easy look up
    cursor.execute('Select * from rating where userid=%s',  session["Id"])
    target_rated_movies = cursor.fetchall()
    target_rated_movies_dict = {}
    for tr in target_rated_movies:
        target_rated_movies_dict[str(tr["MovieId"])] = tr["Rating"]

    # Loop through every movie in the similarity csv, if the user has not rated the movie, find the most similar movie
    # that the user has rated to this movie and use the value that they gave for the rated movie for the unrated movie
    recommended_movies = {}
    with open('item_based_recommendations.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            if row != []:
                if str(row[0]) not in target_rated_movies_dict:
                    for col in row:
                        if str(col) in target_rated_movies_dict:
                            recommended_movies[titleDict[str(row[0])]] = str(target_rated_movies_dict[str(col)])
                            break

    recommended_movies = sorted(recommended_movies.items(), key=itemgetter(1), reverse=True)
    return render_template('itembased.html', recommended_movies=recommended_movies)

@app.route('/evaluation', methods=['GET'])
def evaluate():
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    # check if user has rated movies
    # if not, display "invalid" page
    cursor.execute('select count(*) as count from rating where userid = %s', (session['Id']))
    rating_count = cursor.fetchone()
    if int(rating_count['count']) == 0:
        return render_template('invalid.html')

    with open('ratings.csv') as csvfile:
        ratings = csvfile.read().split('\n')
        # use numpy to convert list to numpy array
        ratings = numpy.array(ratings)
        print(ratings)
        # use sci-kit learn to split the data
        ratings_train, ratings_test = train_test_split(ratings, test_size=0.2)

        # remove previous entries so we can randomize our test data
        cursor.execute("DROP table if exists RatingTrain")
        connection.commit()
        #
        cursor.execute("DROP table if exists RatingTest")
        connection.commit()

        # create training and test tables
        statement = 'create table RatingTrain( \
        UserId int Not Null,\
        MovieId int Not Null,\
        Rating real Not Null, \
        Primary Key(UserId, MovieId), \
        Foreign key(UserId) References User(Id) on delete cascade,\
        Foreign key(MovieId) References Movie(Id) on delete cascade);'
        cursor.execute(statement)
        connection.commit()

        statement = 'create table RatingTest( \
                UserId int Not Null,\
                MovieId int Not Null,\
                Rating real Not Null, \
                Primary Key(UserId, MovieId), \
                Foreign key(UserId) References User(Id) on delete cascade,\
                Foreign key(MovieId) References Movie(Id) on delete cascade);'
        cursor.execute(statement)
        connection.commit()
        # split up the train and test data
        ratings_train = ratings_train.tolist()
        ratings_test = ratings_test.tolist()

        # insert the train set to the db
        for current_rating in ratings_train:
            if current_rating != list():
                rating = current_rating.split(',')
                if rating != [''] and rating[0] != 'userId':
                    cursor.execute('INSERT INTO RATINGTRAIN (UserId, MovieId, Rating) VALUES(%s, %s, %s)', (str(rating[0]), str(rating[1]), str(rating[2])))
                    connection.commit

        # insert the test set to the db
        for current_rating in ratings_test:
            if current_rating != list():
                rating = current_rating.split(',')
                if rating != [''] and rating[0] != 'userId':
                    cursor.execute('INSERT INTO RATINGTEST (UserId, MovieId, Rating)  VALUES(%s, %s, %s)', (str(rating[0]), str(rating[1]), str(rating[2])))
                    # cursor.execute(query, (rating[0], rating[1], rating[2]))
                    connection.commit
    userbased_MAE, userbased_accuracy = runUserBasedTest()
    itembased_MAE, itembased_accuracy = runItemBasedTest()

    return render_template('metrics.html', userbased_MAE=userbased_MAE, userbased_accuracy=userbased_accuracy, itembased_MAE=itembased_MAE, itembased_accuracy=itembased_accuracy)

def runUserBasedTest():
    now = datetime.now()
    start_time = now.strftime("%H:%M:%S")
    MAE = 0
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    cursor.execute('SELECT * FROM RatingTest')
    ratings_test = cursor.fetchall()

    similarityList = {}
    correctPredictions = 0
    totalPredictions = 0
    # Loop through each rating in the ratings test set and compute the prediction
    # then aggregate the value to the numerator of the MAE
    for current_test_rating in ratings_test:
        if current_test_rating != list():

            # Get the current test user's rating info
            userid = str(current_test_rating["UserId"])
            movieid = str(current_test_rating["MovieId"])
            rating = decimal.Decimal(current_test_rating["Rating"])

            # retrieve the avg rating from the target user to calculate the prediction
            cursor.execute("select avg(rating) as avg_rating from ratingtest where userid = %s", str(userid))
            target_avg_rating_dict = cursor.fetchone()
            target_avg_rating = target_avg_rating_dict['avg_rating']

            # check if the system has already predicted for target user
            # if so, we can retrieve its similar users dictionary from before
            if userid not in similarityList:
                current_similarities = computePearsonSimTest(userid)
                similarityList[str(userid)] = current_similarities
            i=0
            cursor.execute('select * from rating where movieid = %s', movieid)
            targetMovieRatings = cursor.fetchall();

            # store the current movie ratings in a dictionary
            currentMovieRatings = {}
            for currentRating in targetMovieRatings:
                currentMovieRatings[currentRating["UserId"]] = currentRating["Rating"]

            # Loop the current similarities and find the first 3 users (sorted = Decreasing) who have rate the movie
            den = 0
            num = 0
            for x, y in similarityList[userid]:
                if i == 3:
                    break

                # check if current similar user has rated the test movie
                # if so, aggregate the values need to compute the weighted average prediction later
                if x in currentMovieRatings:
                    cursor.execute("select avg(rating) as avg_rating from ratingtest where userid = %s", str(x))
                    current_avg_rating = cursor.fetchone()
                    den = den + abs(y)
                    num = num + ((decimal.Decimal(currentMovieRatings[x])-decimal.Decimal(current_avg_rating['avg_rating']))*y)
                    i=i+1
            # if den is really small, assume the sum of the similarities is 0 instead of getting a extremely large value back
            if den == 0:
                predictedRating = decimal.Decimal(target_avg_rating) + 0
            else:
                predictedRating = abs(decimal.Decimal(target_avg_rating) + (num / den))
                if abs(rating-predictedRating) > 5:
                    predictedRating = 5
            # Round the predicted rating to the nearest multiple of 0.5
            predictedRating = abs(decimal.Decimal(round(predictedRating*2)/2))
            MAE = MAE + abs(rating-predictedRating)
            if predictedRating == decimal.Decimal(rating):
                correctPredictions = correctPredictions + 1
            totalPredictions = totalPredictions + 1

    accuracy = str(round(((correctPredictions/totalPredictions)*100),2))+"%"
    now = datetime.now()
    end_time = now.strftime("%H:%M:%S")
    print("start time: "+str(start_time))
    print("end time: "+str(end_time))
    return MAE, accuracy


def computePearsonSimTest(user_id):
    # create  dictionary to store every movie as the key and its similar movies in decreasing order as the values
    # this allows for easy lookup of the user and then scan for similar users
    pearson_similarities = {}
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("select avg(rating) as avg_rating from ratingtest where userid = %s", user_id)
    rating_dict = cursor.fetchone()
    target_avg_rating = rating_dict['avg_rating']

    # retrieve the ratings for current test user
    cursor.execute("select * from ratingtest where userid = %s", user_id)
    target_user_ratings = cursor.fetchall()
    # retrieve id's of users
    cursor.execute("select id from user")
    id_arr = cursor.fetchall()

    # Loop through every user except target
    # Compute similarity on target and current user ratings
    for current_id in id_arr:
        # Ensure we do not compute similarity on target user
        if current_id["id"] != user_id:
            # Get the current user's ratings and avg rating
            cursor.execute("select * from ratingtest where userid = %s", current_id["id"])
            current_user_ratings = cursor.fetchall()
            cursor.execute("select avg(rating) as avg_rating from ratingtest where userid = %s", current_id['id'])
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

    # sort the similarities for easy scanning
    pearson_similarities = sorted(pearson_similarities.items(), key=itemgetter(1), reverse=True)
    connection.commit()
    return pearson_similarities;

def runItemBasedTest():

    # Initialize connection, MAE and time structure
    now = datetime.now()
    start_time = now.strftime("%H:%M:%S")
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("select * from ratingtest")
    test_ratings = cursor.fetchall()
    MAE = 0

    # store item matrix in dictionary for easy lookup
    item_matrix = {}
    i=0
    with open('item_based_recommendations.csv', 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        # skip the headers
        header = next(reader)
        for row in reader:
            tempList = []
            i = 0
            for col in row:
                 if i != 0:
                    tempList.append(col)
                 i = i + 1
            item_matrix[row[0]] = tempList

    # Initialize data structures to compute accuracy
    test_users_ratings = {}
    correctPredictions = 0
    totalPredictions = 0

    # Loop each test rating...
    for current_test_rating in test_ratings:
        userid = str(current_test_rating["UserId"])
        movieid = str(current_test_rating["MovieId"])
        rating = decimal.Decimal(current_test_rating["Rating"])

        # check if the system has already predicted a movie for the current test user
        # if not, store the current test user's ratings for easy lookup
        if userid not in test_users_ratings:
            cursor.execute('select * from ratingtest where userid = %s', str(userid))
            current_user_rating = cursor.fetchall()
            current_user_rating_dict = {}
            for current_rating in current_user_rating:
                current_user_rating_dict[str(current_rating['MovieId'])] = current_rating['Rating']
            test_users_ratings[userid] = current_user_rating_dict

        # Loop through every current similar movies of the current test movie
        # and find the first / most similar movie in that list that was rated by
        # the current test user and label the test movie prediction
        # to be the rating for the similar movie given by the user.
        for currentSimilarMovie in item_matrix[movieid]:
            if currentSimilarMovie in test_users_ratings[userid]:
                prediction = test_users_ratings[userid][currentSimilarMovie]
                actual = rating
                MAE = MAE + abs(decimal.Decimal(actual) - decimal.Decimal(prediction))
                if decimal.Decimal(actual) == decimal.Decimal(prediction):
                    correctPredictions = correctPredictions + 1
                totalPredictions = totalPredictions + 1
                break

    accuracy = str(round(((correctPredictions/totalPredictions)*100),2))+"%"

    # print out time info to see how long function takes
    now = datetime.now()
    end_time = now.strftime("%H:%M:%S")
    print("start time: " + str(start_time))
    print("end time: " + str(end_time))
    print(MAE)

    return MAE, accuracy


if __name__ == '__main__':
    app.run(debug=True)