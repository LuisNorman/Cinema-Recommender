# Cinema-Recommender
A flask web app that host a movie recommendation system which utilizes user-based and item-based collaborative filtering 
to make recommendations. Users have the ability to register/login, rate movies, and in return, recieve recommendations.
The dataset used was collected by MovieLens and contains roughly 600 users, 9,000 movies, and 100,000 ratings.

## Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. 
To note, the project was developed in MacOS therefore the installation instructions are for MacOS.

### Prerequisites
MySQL
```
1. Download and install the latest version of MySQL.
```

MySQL Workbench
```
1. Download and install MySQL Workbench.
```

Python
```
1. Download Python.
2. Download an IDE (PyCharm) instead of bare text editor for help importing packages. 
```

### Installing

A step by step series of examples that tell you how to get a development environment running.

Step 1.

```
Start MySQL
```

Step 2.  

```
Open MySQL Workbench
```

Step 3.

```
Create a connection in MySQL Workbench
```

Step 4.

```
Create a database named "Cinemarecommender" in MySQL Workbench
```

Step 5.

```
Create a user named "testuser" and password named "test123" that can access the cinema recommender database in MySQL Workbench
```

Step 6.

```
Run the script named "insert_create.py" to create and insert the tables and data into MySQL
```

Step 7.

```
Open an IDE 
```

Step 8.

```
Open the project folder named "Cinema Recommender" in the IDE
```

Step 9.

```
Run the main application named "app.py" 
```

### How to use

A step by step series of examples that tell you how to rate movies and recieve recommendations.


Step 1.

```
Go to a web browser and go to "localhost:5000"
```

Step 2.

```
Register (if first time user) and login
```

Step 3.

```
Navigate to the "Profile" page and rate movies (You most rate movies in order to recieve recommendations)
```

Step 4.

```
Navigate to the "User Based" or "Item Based" page to browse recommendations
```

Step 5.

```
Navigate to the "Metrics" page to view the accuracy and mean absolute error of both methods
```
