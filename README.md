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
