# MOVIES-FOR-FRIENDS
CS50 Webtrack Final Project Website creating personalized lists for movie fans.

On [MOVIES-FOR-FRIENDS (MFF)](https://movies-for-friends.herokuapp.com) website you can set up an account and make a list of movies you have seen or would like to see, give a personal rating and add them to "best of" if required.

You can also see what other users are adding to their lists, and see the average ratings for a given movie but without identifying and single user or their individual ratings.

Who is this for?

MOVIES-FOR-FRIENDS is useful to anyone if they would like to keep track of which movies they have seen and how they liked them, and keep an eye on what they would like to watch next. There is also a social element, thanks to 'pooling' of other users' ratings and lists.

- You sit down to watch a movie. What was it you wanted to watch the other day? Make a watchlist with MFF!
- What is your favourite movie? What is your favourite comedy film? You can now make your own favourite lists.
- How did you like the movie you have just watched? Although thousands of IMDB viewers rated it very highly, MFF users' average rating is very low? How about you?
- How many other MFF users have the same favourite movies as you?

Of course you can use IMDB for achieving most of the same functionality but I personally found it to be cumbersome particularly because although you can define your own lists, they are not easy to compare with other users.

Technologies Used

    The idea and initial skeleton of the website was inspired by "Finance" website as part of Hardvard's CS50 Web Development Track.
    Flask web framework.
    Bootstrap 4.0 CSS layout.
    Heroku web-hosting.
    PostgreSQL database.
    OMDb API movie details under CC BY-NC 4.0 licence.

How to Use the site:

- Register with a username and password of your choice (no restrictions)
- Search a movie using any word in its title
- Select the right one from the list of search hits
- You can then do one or more of the following
    - Add to your watchlist
    - Mark as watched
    - Rate it (with a deliberately restricted scale) : Awful, Bad, OK, Good, Excellent
    - Add to one of your "Best of" lists

- You can also remove a movie from your list by unticking the "In my list" checkbox

- Commit your changes to the database by clicking on "Save" button

- On the lists screen you can see the number of movies you - and others - have on their lists e.g. watched, rated, watchlist etc.

- If you click on any of these, you will be presented with a list of all the movies in that category

HAVE FUN!