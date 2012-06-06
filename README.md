# GitZen

This is a web application built using Django that links Zendesk and Github for easier developer management.

### Deploying the application to Heroku (on Ubuntu)

1. Make a Heroku account on their [website](http://www.heroku.com/).

2. Install the Heroku toolbet using the command
	>`wget -qO- https://toolbelt.heroku.com/install.sh | sh`

3. Login to Heroku by running the command
	>`heroku login`
	
	and filling out the requested credentials.

4. Install python and virtualenv. (A guide for this can be found [here](http://docs.python-guide.org/en/latest/starting/install/linux/))

5. Install a version of Postgres from [here](http://www.postgresql.org/download/) so testing can be done locally.

6. Clone the GitZen repo with the command
	>`git clone git://github.com/FriedRice/GitZen.git`

7. Change directories to the newly cloned GitZen directory and setup a virualenv using the command
	>`virtualenv venv --distribute`

8. Activate the virtualenv with the command
	>`source venv/bin/activate`  
		
	You must source the virtualenv environment for each terminal session where you wish to run your app.

9. Run the command
	>`sudo apt-get install libpq-dev python-dev`

	to install the necessary packages that allow for the installation of psycopg2 (Postgresql support for python) in the following step.

10. Install the required packages for GitZen and Heroku with pip by using the command
	>`pip install -r requirements.txt`

11. Create the app on the Heroku Cedar stack by running the command
	>`heroku create --stack cedar`

12. Deploy the app with the command
	>`git push heroku master`

13. The command
	>`heroku logs`

	can be used to view the logs of the app if desired, and the command
	>`heroku open`

	can be used to visit the app on the web.

14. In order to conduct one-off admin processes for the app in django, preface the commands with
	>`heroku run`

	An example of this would be syncing the databases in django by using the command
	>`heroku run python manage.py syncdb`

### Configuration Instructions

1. Go to the [GitZen website](http://gitzen.herokuapp.com) on Heroku.

2. Located under the heading "New User", begin filling out the information to create a new user by first assigning them a username and password and filling the "Username", "Password", and "Affirm Password" fields with this information.

3. In order to use GitHub ticket information in GitZen, each user must provide a set of access information from a GitHub account linked to the repository from which the ticket information should be monitored. This access information consists of a GitHub username, repository name, and API key associated with the desired ticket information, and those access parameters should be filled into the "GitHub Username", "GitHub Repository", and "GitHub API Key" fields in the new user form respectively.

4. In order to use Zendesk ticket information in GitZen, each user must provide a set of access information from a Zendesk account linked to the tickets that should be monitored. The first information required to access this data is a Zendesk user email and password, and those access parameters should be filled into the "Zendesk User Email" and "Zendesk Password" fields in the new user form respectively. The other three bits of Zendesk access information needed are more specific and are covered in the following steps.

5. For the "Zendesk URL" field in the new user form, enter in the full URL that comes up after logging into a Zendesk account associated with the desired ticket information.

6. For the "Zendesk Ticket View ID" field in the new user form, enter in the ID number assigned by Zendesk to the desired group of tickets.

7. For the "Zendesk Ticket Association Field" field in the new user form, enter in the full name of the field that holds the external ticket association data for each Zendesk ticket. If a defualt named was used for this field, the name will probably be in the format "field-######" where the "#" are numbers between 0-9.

8. Check to see that all fields under the "New User" heading are filled out accuracely, and then click the "Create User" button to create a user with the given information. A confirmation page should come up after this process that will have a link to return to the login screen.

