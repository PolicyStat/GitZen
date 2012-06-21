# GitZen

This is a web application built using Django that links Zendesk and Github for
easier developer management.

### Setting up the environment for Heroku deployment (on Ubuntu)

1. Make a Heroku account on their [website](http://www.heroku.com/).

2. Install the Heroku toolbet using the command
	>`wget -qO- https://toolbelt.heroku.com/install.sh | sh`

3. Login to Heroku by running the command
	>`heroku login`

	and filling out the requested credentials.

4. Install python and virtualenv. (A guide for this can be found
[here](http://docs.python-guide.org/en/latest/starting/install/linux/))

5. Install a version of Postgres from
[here](http://www.postgresql.org/download/) so testing can be done locally.

6. Clone the GitZen repo with the command
	>`git clone git://github.com/FriedRice/GitZen.git`

7. Change directories to the newly cloned GitZen directory and setup a virualenv
using the command
	>`virtualenv venv --distribute`

8. Activate the virtualenv with the command
	>`source venv/bin/activate`  
		
	You must source the virtualenv environment for each terminal session where
you wish to run your app.

9. Run the command
	>`sudo apt-get install libpq-dev python-dev`

	to install the necessary packages that allow for the installation of
psycopg2 (Postgresql support for python) in the following step.

10. Install the required packages for GitZen and Heroku with pip by using the
command
	>`pip install -r requirements.txt` 

### Deploying the application to Heroku (on Ubuntu)

1. Create the app on the Heroku Cedar stack by running the command
	>`heroku create --stack cedar`

2. Deploy the app with the command
	>`git push heroku master`

3. The command
	>`heroku logs`

	can be used to view the logs of the app if desired, and the command
	>`heroku open`

	can be used to visit the app on the web.

4. In order to conduct one-off admin processes for the app in django, preface
the commands with
	>`heroku run`

	An example of this would be syncing the databases in django by using the
command
	>`heroku run python manage.py syncdb`

### Configuration Instructions

1. Go to the [GitZen website](http://gitzen.herokuapp.com) on Heroku.

2. Located under the heading "New User", begin filling out the information to
create a new user by first assigning them a username and password and filling
the "Username", "Password", and "Affirm Password" fields with this information.

3. In order to use GitHub ticket information in GitZen, each user must provide a
set of access information from a GitHub account linked to the repository from
which the ticket information should be monitored. This access information
consists of a GitHub username, password, organization name, and repository name
associated with the desired ticket information, and those access parameters
should be filled into the "GitHub Username", "GitHub Password", "GitHub
Organization", and "GitHub Repository" fields in the new user form respectively.
If the repository is under a user account rather than an organization, provide
the username of that account in the organization field instead.

4. In order to use Zendesk ticket information in GitZen, each user must provide
a set of access information from a Zendesk account linked to the tickets that
should be monitored. The first information required to access this data is a
Zendesk user email which should be filled into the "Zendesk User Email" field in
the new user form. The other three bits of Zendesk access information needed are
more specific and are covered in the following steps.

5. In order to allow API token access to the Zendesk account, "Token Access"
must be enabled. This option can be found by logging into Zendesk with an
account that has administrator level credentials and looking under
"Settings"->"Channels"->"API". After clicking "edit" and checking the "Token
Access" box, copy the displayed API token and paste it into the "Zendesk API
Token" field in the new user form.

6. For the "Zendesk URL" field in the new user form, enter in the full URL that
comes up after logging into the Zendesk account associated with the desired
ticket information (The URL should be in the format
"https://\{yourcompanyname\}.zendesk.com").

7. For the "Zendesk Ticket Association Field ID" field in the new user form, the
ID number of the field that holds the external ticket association data for each
Zendesk ticket must be found. In order to find this ID number, first look up the
ID number of a Zendesk ticket from the desired account that has this ticket
association field on it. Then open up a command terminal and enter in the
following command, substituting the parameters surrounded by braces with the
information from the desired Zendesk account and substituting the `id` parameter
with the ticket ID number that was just looked up:
	>`curl {zendesk_url}/api/v2/tickets/{id}.json -u
	>{email_address}/token:{api_token}`

	From the output of this command, look for the dictionary key "fields", and
within the dictionaries listed for the value of this key, look for the one with
the value of the "value" key matching the value of the ticket association field
of the Zendesk ticket that was looked up for this process. In the same
dictionary as this "value" pair, the number value for the "id" key is the ID
number that must be entered into the "Zendesk Ticket Association Field ID" field
in the new user form.

8. For the "Age Limit (in days) for the Tickets" field in the new user form,
enter a limit (in days) for the age of the tickets used in the application.
Only tickets from Zendesk and GitHub that were last updated between the current
time and this age limit away from the current time will be monitored in the
application. It should be noted that the higher this age limit is set, the
longer it will take to load the application on login, so for this reason, it is
recommended that the age limit is not set higher than one year (365 days) to
avoid load times that are too long for Heroku. 

9. Check to see that all fields under the "New User" heading are filled out
accurately, and then click the "Create User" button to create a user with the
given information. A confirmation page should come up after this process that
will have a link to return to the login screen.
